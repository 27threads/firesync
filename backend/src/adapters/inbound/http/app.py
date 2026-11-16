"""FastAPI composition root. Run with uvicorn ...:create_app --factory."""
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from hashlib import sha256
import json
import logging
import os
from time import monotonic as system_monotonic

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from backend.adapters.inbound.http.cache import ResponseCache
from backend.adapters.inbound.http.limits import RateLimiter
from backend.adapters.inbound.http.zip_export import audit_zip
from backend.adapters.outbound.config_file.rules import load_risk_rules, load_rules
from backend.adapters.outbound.llm.openai import ProviderChain
from backend.application.api import calculate_calendar, calendar_cache_key, parse_request
from backend.application.assistant import AskService, validate_messages, worth_caching
from backend.application.assistant_tools import Toolbox
from backend.application.audit import audit_document
from backend.domain.calculations.map_features import map_result
from backend.domain.models.error import CalendarError
from backend.domain.models.map_query import MapQuery
from backend.ports.api import ApiRepository

logger = logging.getLogger('uvicorn.error.firesync')
# A drawn polygon is a few KB; this stops huge bodies before they reach memory or Shapely.
MAX_BODY_BYTES = 1_000_000
ERROR_STATUS = {'invalid_geometry': 400, 'invalid_period': 400, 'invalid_bbox': 400,
                'invalid_hours': 400, 'invalid_mode': 400, 'region_not_found': 404, 'area_too_large': 413,
                'invalid_request': 400, 'assistant_unavailable': 503}


def assistant_from_env(llm, clock):
    """A bad assistant setting turns the assistant off; it must never stop the rest of the API from starting."""
    try:
        llm = llm or ProviderChain.from_env(os.environ.get('ASSISTANT_PROVIDERS', ''),
                                            float(os.environ.get('ASSISTANT_TIMEOUT_S', 20)))
        return llm, AskService(llm, int(os.environ.get('ASSISTANT_DAILY_LIMIT', 500)), clock,
                               float(os.environ.get('ASSISTANT_BUDGET_S', 60)))
    except ValueError as error:
        logger.error('Assistant disabled, invalid configuration: %s', error)
        return None, None


def error_response(code, message, status, headers=None):
    return JSONResponse({'error': {'code': code, 'message': message}}, status_code=status, headers=headers)


def create_app(repository: ApiRepository | None = None, clock=None, monotonic=None,
               limits=None, rate_window=None, frontend_origin=None, client_ip_header=None, llm=None):
    clock = clock or (lambda: datetime.now(UTC))
    # Only set behind a proxy that overwrites the header (CF-Connecting-IP with Cloudflare Tunnel);
    # otherwise any client could pick its own rate-limit bucket.
    client_ip_header = client_ip_header or os.environ.get('CLIENT_IP_HEADER', '')
    monotonic = monotonic or system_monotonic
    rules = load_rules()
    risk_rules = load_risk_rules()
    configured_limits = limits if limits is not None else {
        key: int(os.environ.get('RATE_LIMIT_' + key.upper(), default))
        for key, default in [('general', 60), ('calendar', 10), ('export', 2), ('ask', 5)]}
    limiter = RateLimiter(configured_limits, rate_window if rate_window is not None else int(os.environ.get('RATE_LIMIT_WINDOW', 60)), monotonic)
    cache = ResponseCache(int(os.environ.get('RESPONSE_CACHE_SIZE', 128)))
    # Without ASSISTANT_PROVIDERS the assistant is off and /ask answers 503; nothing else depends on it.
    llm, assistant = assistant_from_env(llm, clock)

    @asynccontextmanager
    async def lifespan(app):
        nonlocal repository
        pool = None
        try:
            if repository is None:
                from psycopg_pool import ConnectionPool
                from backend.adapters.outbound.postgres.api import PostgresApiRepository
                pool = ConnectionPool(os.environ['DATABASE_URL'], min_size=1, max_size=4, open=False)
                await run_in_threadpool(pool.open, wait=True)
                repository = PostgresApiRepository(pool, rules)
            # Metadata checks include H3 resolution and a sample of actual cells.
            def validate():
                with repository.read() as reader:
                    reader.meta()
            await run_in_threadpool(validate)
            yield
        finally:
            if pool is not None:
                await run_in_threadpool(pool.close)

    app = FastAPI(title='firesync API', version='1.0', lifespan=lifespan)

    @app.middleware('http')
    async def guard(request: Request, call_next):
        started = monotonic()
        try:
            endpoint = request.url.path.rsplit('/', 1)[-1]
            client_ip = (client_ip_header and request.headers.get(client_ip_header)) or (
                request.client.host if request.client else 'unknown')
            wait = limiter.retry_after(client_ip, endpoint)
            if wait and request.method != 'OPTIONS':
                response = error_response('rate_limited', 'Too many requests. Try again later.', 429, {'Retry-After': str(wait)})
            else:
                response = await call_next(request)
        except CalendarError as error:
            status = ERROR_STATUS.get(error.code, 500)
            response = error_response(error.code if status != 500 else 'internal_error',
                                      str(error) if status != 500 else 'Unable to process the request.', status)
        except Exception:
            logger.exception('Request failed: %s', request.url.path)
            response = error_response('internal_error', 'Unable to process the request.', 500)
        logger.info('endpoint=%s status=%s duration_ms=%.1f n_cells=%s', request.url.path,
                    response.status_code, (monotonic() - started) * 1000, getattr(request.state, 'n_cells', 0))
        return response

    app.add_middleware(CORSMiddleware,
        allow_origins=[frontend_origin or os.environ.get('FRONTEND_ORIGIN', 'http://localhost:5173')],
        allow_methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Content-Type', 'If-None-Match'],
        expose_headers=['ETag', 'Retry-After', 'Content-Disposition'])

    def json_response(request, body, meta, key):
        version = meta['updated_at'] + meta['data_version'] + key
        etag = '"' + sha256(version.encode()).hexdigest() + '"'
        headers = {'ETag': etag, 'Cache-Control': 'no-cache'}
        if request.method == 'GET' and request.headers.get('if-none-match') == etag:
            return Response(status_code=304, headers=headers)
        return JSONResponse(body, headers=headers)

    @app.get('/api/v1/health')
    def health(request: Request):
        with repository.read() as reader:
            meta = reader.meta()
            return json_response(request, {'status': 'ok', **{k: v for k, v in meta.items() if k != 'scale'}}, meta, 'health')

    @app.get('/api/v1/regions')
    def regions(request: Request):
        with repository.read() as reader:
            meta = reader.meta()
            return json_response(request, reader.regions(), meta, 'regions')

    async def read_body(request):
        def reject_nonfinite(_value):
            raise ValueError('Nonfinite numbers are not valid JSON.')
        if int(request.headers.get('content-length') or 0) > MAX_BODY_BYTES:
            raise CalendarError('area_too_large', 'The request body is too large.')
        body = bytearray()
        async for chunk in request.stream():  # also caps bodies sent without Content-Length
            body += chunk
            if len(body) > MAX_BODY_BYTES:
                raise CalendarError('area_too_large', 'The request body is too large.')
        try:
            return json.loads(bytes(body), parse_constant=reject_nonfinite)
        except (ValueError, UnicodeError):
            raise CalendarError('invalid_geometry', 'A valid JSON request is required.') from None

    def calendar_response(request, payload):
        area, start, end = parse_request(payload)
        now = clock()
        key = json.dumps(payload, sort_keys=True, allow_nan=False) + now.date().isoformat()
        with repository.read() as reader:
            meta = reader.meta()
            cache_key = calendar_cache_key(payload, now.date(), meta)
            body = cache.get(cache_key)
            if body is None:
                _, body = calculate_calendar(reader, area, start, end, now.date(), rules)
                cache.put(cache_key, body)
            request.state.n_cells = body['area']['n_cells']
            return json_response(request, body, meta, key)

    @app.post('/api/v1/calendar')
    async def calendar(request: Request):
        return await run_in_threadpool(calendar_response, request, await read_body(request))

    def export_response(request, payload):
        area, start, end = parse_request(payload)
        now = clock()
        with repository.read() as reader:
            snapshot, result = calculate_calendar(reader, area, start, end, now.date(), rules)
            request.state.n_cells = result['area']['n_cells']
            files, metadata = audit_document(reader, snapshot, result, payload, now, rules)
        return Response(audit_zip(files, metadata), media_type='application/zip',
                        headers={'Content-Disposition': f'attachment; filename="firesync-{now.date()}.zip"'})

    @app.post('/api/v1/export')
    async def export(request: Request):
        return await run_in_threadpool(export_response, request, await read_body(request))

    @app.get('/api/v1/detections/recent')
    def detections(request: Request):
        params = request.query_params
        query = MapQuery.parse(params.get('bbox'), params.get('hours', '24'), params.get('zoom', '4'), params.get('mode', 'auto'))
        with repository.read() as reader:
            meta = reader.meta()
            key = ('map', query, meta['updated_at'], meta['data_version'])
            now = clock()
            cached = cache.get(key)
            if cached is None or now > cached[1]:
                rows = reader.map_rows(query, now)
                body = map_result(query, rows, meta['updated_at'], rules, risk_rules)
                expires_at = rows['expires_at']
                cache.put(key, (body, expires_at))
            else:
                body, expires_at = cached
            return json_response(request, body, meta, repr(query) + expires_at.isoformat())

    def ask_response(payload):
        messages = validate_messages(payload)
        if llm is None:
            raise CalendarError('assistant_unavailable', 'Assistant unavailable, use the map.')
        now = clock()
        with repository.read() as reader:  # short: the tools open their own reads, none waits on the model
            meta = reader.meta()
        # First questions (the suggested ones) repeat a lot: cache them until the data or the day changes.
        key = (('ask', messages[0]['content'], now.date().isoformat(), meta['updated_at'], meta['data_version'])
               if len(messages) == 1 else None)
        body = cache.get(key) if key else None
        if body is None:
            body = assistant.ask(messages, Toolbox(repository, meta, now, rules, risk_rules, cache))
            body['meta'] = {'updated_at': meta['updated_at'], 'data_version': meta['data_version']}
            if key and worth_caching(messages[0]['content'], body):  # untraced figures, wrong language: not reused
                cache.put(key, body)
        return JSONResponse(body, headers={'Cache-Control': 'no-store'})

    @app.post('/api/v1/ask')
    async def ask(request: Request):
        try:
            payload = await read_body(request)
        except CalendarError as error:
            if error.code != 'invalid_geometry':
                raise
            raise CalendarError('invalid_request', 'A valid JSON request is required.') from None
        return await run_in_threadpool(ask_response, payload)

    return app
