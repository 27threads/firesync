from dataclasses import replace
from datetime import date
import pytest

from backend.domain.models.area import Area
from backend.domain.models.error import CalendarError
from backend.domain.models.month import Month
from backend.domain.models.snapshot import HistorySnapshot
from backend.domain.calculations.history import aligned, annual_results, month_scenarios, seasonality_results, total
from backend.services.calendar import CalendarService
from tests.fakes.history import FakeHistoryRepository


def fixture(counts=(), factors=(), **changes):
    snapshot = HistorySnapshot(
        meta={'last_month':'2026-11', 'updated_at':'2026-11-14T15:00:00Z','data_version':'2026-11-14', 'h3_resolution':6,'scale':'VIIRS'},
        area={'type':'region','n_cells':1,'area_km2':36,'biomes':[{'region_id':1,'name':'Test','fraction':1}]},
        coverage={'status':'full','covered_fraction':1,'message':None},
        counts=tuple(counts), factors=tuple(factors),
        periods=({'region_id':1,'satellite':'Aqua','start':date(2003,1,1),'end':date(2012,1,31)},
                 {'region_id':1,'satellite':'SNPP','start':date(2012,2,1),'end':date(2026,10,31)},
                 {'region_id':1,'satellite':'N20','start':date(2026,11,1),'end':date(2026,11,14)}),
        missing=frozenset(),provisional=frozenset())
    return replace(snapshot, **changes)


def count(year, month, amount, satellite=None, region=1, daynight='D'):
    return {'year':year,'month':month,'raw_count':amount,'region_id':region,
            'satellite':satellite or Month(year,month).satellite,'daynight':daynight}


def factors(month, values, region=1, daynight='D'):
    return [{'region_id':region,'month':month,'daynight':daynight,'calibration_year':year,'factor':value}
            for year,value in values.items()]


def run(snapshot, start, end):
    repository = FakeHistoryRepository(snapshot)
    service = CalendarService(repository, clock=lambda:date(2026,11,14))
    result = service.calculate(Area('region',region_id=1), start, end)
    assert repository.calls == 1
    return result


def test_estimate_uses_each_scenario_before_sum():
    snapshot = fixture([count(2003,1,2),count(2003,1,3,daynight='N')],
                       factors(1,{2013:1,2014:3}) + factors(1,{2013:4,2014:2},daynight='N'))
    month = run(snapshot,'2003-01','2003-01')['months'][0]
    # E_2013=2*1+3*4=14; E_2014=2*3+3*2=12.
    assert month['detections'] == 13
    assert month['band_low'] == pytest.approx(12.1)
    assert month['band_high'] == pytest.approx(13.9)
    assert month['raw_count'] == 5


def test_observed_counts_use_only_one_satellite_without_factor():
    result = run(fixture([count(2026,11,7),count(2026,11,99,'SNPP')]),'2026-11','2026-11')
    month = result['months'][0]
    assert month['detections'] == 7
    assert month['band_low'] is None
    assert month['incomplete'] is True
    assert month['anomaly'] is None
    assert result['years'][0]['rank'] is None


def test_zero_missing_and_provisional_are_distinct():
    missing = frozenset((date(2020,2,d),'SNPP') for d in (1,2,3)) | {(date(2020,2,4),'Aqua')}
    result = run(fixture(missing=missing,provisional=frozenset({(2020,2,'SNPP')})), '2020-01','2020-03')
    assert len(result['months']) == 3
    assert result['months'][0]['detections'] == 0
    assert result['months'][0]['incomplete'] is False
    assert result['months'][1]['missing_days'] == 3
    assert result['months'][1]['incomplete'] is True
    assert result['months'][1]['provisional'] is True
    assert result['months'][0]['anomaly_pct'] is None


def test_outside_coverage_has_no_zero_calendar():
    result = run(fixture(coverage={'status':'none','covered_fraction':0,'message':'No data.'}),'2020-01','2020-02')
    assert set(result) == {'meta','area','coverage'}


def test_missing_factors_and_temporal_coverage_fail_explicitly():
    with pytest.raises(CalendarError,match='factors'):
        run(fixture([count(2003,1,1)]),'2003-01','2003-01')
    with pytest.raises(CalendarError,match='temporal coverage'):
        run(fixture(periods=()),'2020-01','2020-01')


@pytest.mark.parametrize('start,end',[('2002-12','2020-01'),('2020-02','2020-01'),('2026-12','2026-12')])
def test_period_bounds(start,end):
    with pytest.raises(CalendarError) as error:
        run(fixture(),start,end)
    assert error.value.code == 'invalid_period'


def test_anomaly_reference_does_not_depend_on_requested_filter():
    # Three complete reference years with September totals 10,30,50.
    periods=({'region_id':1,'satellite':'SNPP','start':date(2019,1,1),'end':date(2021,12,31)},)
    data=fixture([count(2019,9,10),count(2020,9,30),count(2021,9,50)],periods=periods,
                 meta={'last_month':'2021-12'})
    small=run(data,'2020-09','2020-09')['months'][0]
    large=run(data,'2019-01','2021-12')['months'][20]
    assert small['anomaly'] == large['anomaly'] == 0
    assert small['anomaly_pct'] == large['anomaly_pct'] == 0


def test_annual_totals_sum_scenarios_not_monthly_medians():
    # Monthly medians sum to zero, but annual scenarios are [10,10,10].
    vectors={Month(2003,1):{2013:10,2014:0,2015:0},Month(2003,2):{2013:0,2014:10,2015:0},
             Month(2003,3):{2013:0,2014:0,2015:10}}
    annual=annual_results(list(vectors),vectors,date(2026,11,14))[0]
    assert annual['detections'] == 10
    assert annual['band_low'] == annual['band_high'] == 10
    assert annual['rank'] is None


def test_common_scenarios_are_aligned_by_year_not_position():
    assert total([{2013:5,2014:8},{2012:100,2013:2,2014:1},{None:7}]) == {2013:14,2014:16}
    with pytest.raises(CalendarError,match='common'):
        aligned([{2013:1},{2014:1}])


def test_year_ranking_seasonality_and_latest_indicator():
    counts=[count(year,month,value) for year,value in [(2019,1),(2020,3),(2021,5)] for month in range(1,13)]
    periods=({'region_id':1,'satellite':'SNPP','start':date(2019,1,1),'end':date(2021,12,31)},)
    result=run(fixture(counts,periods=periods,meta={'last_month':'2021-12'}),'2019-01','2021-12')
    assert [r['year'] for r in result['years']] == [2021,2020,2019]
    assert [r['rank'] for r in result['years']] == [1,2,3]
    assert result['seasonality'][0] == {'month_of_year':1,'n_years':3,'median':3,'mean':3,'min':1,'max':5}
    assert result['indicators']['latest_complete_year'] == {'year':2021,'detections':60,'reference_mean':24,'anomaly_pct':1.5}


def test_mixed_year_and_empty_seasonality():
    snapshot=fixture([count(2012,1,2),count(2012,2,5)],factors(1,{2013:3,2014:5}))
    result=run(snapshot,'2012-01','2012-02')
    assert result['years'][0]['source'] == 'mixed'
    assert result['years'][0]['detections'] == 13
    assert result['seasonality'][0]['n_years'] == 0
    assert result['seasonality'][0]['median'] is None


def test_scenario_totals_align_across_biomes():
    vectors,raw=month_scenarios(Month(2003,1),[count(2003,1,2),count(2003,1,3,region=2)],
                               {(1,1,'D'):{2013:1,2014:4},(2,1,'D'):{2013:4,2014:1}})
    assert raw == 5
    assert vectors == {2013:14,2014:11}


def test_seasonality_uses_scenarios_before_summarizing_years():
    vectors={Month(y,m):{2013:a,2014:b,2015:c}
             for y,(a,b,c) in [(2003,(10,0,0)),(2004,(0,10,0)),(2005,(0,0,10))]
             for m in range(1,13)}
    result=seasonality_results([2003,2004,2005],vectors)
    assert result[0]['mean'] == pytest.approx(10/3)
    assert result[0]['median'] == 0
    assert result[0]['max'] == 10


def test_future_month_not_complete_even_when_coverage_is_available():
    result=run(fixture(),'2026-01','2026-11')
    assert result['years'][0]['complete'] is False
    assert result['years'][0]['rank'] is None


def test_no_reference_years_produces_null_anomaly():
    periods=({'region_id':1,'satellite':'SNPP','start':date(2020,1,1),'end':date(2020,12,31)},)
    result=run(fixture([count(2020,1,1)],periods=periods,meta={'last_month':'2020-12'}),'2020-01','2020-12')
    assert result['months'][0]['anomaly'] is None
    assert result['indicators']['latest_complete_year']['reference_mean'] is None
