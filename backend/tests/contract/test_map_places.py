"""Nome do lugar na lista "onde olhar primeiro": quem está no campo reconhece município, unidade de conservação e terra
indígena, não uma célula H3. O job `lugares.py` grava `lugares_celula`; a API só lê e traduz para o contrato."""
import h3

from tests.contract.test_api_contract import client, repository  # noqa: F401 -- shared HTTP fixtures
from tests.contract.test_map_risk import PARENT, URL, scored

PLACE = {'municipality': 'Altamira', 'state': 'PA', 'conservation_units': ['Estação Ecológica da Terra do Meio'],
         'indigenous_lands': ['Kayapó']}


def test_priority_cell_carries_the_name_of_its_place(client, repository):  # noqa: F811 -- pytest injects shared fixtures
    repository.risk = scored(0.72)
    repository.places = {PARENT: PLACE}
    assert client.get(URL).json()['alerts']['priority'][0]['place'] == PLACE


def test_cell_without_a_known_place_has_null_place(client, repository):  # noqa: F811
    """Antes de o job rodar (ou célula fora do Brasil), a lista continua igual, só sem o nome."""
    other = h3.latlng_to_cell(-2.5, -59.5, 4)
    repository.risk = {**scored(0.72), 'by_cell': {PARENT: 0.72, other: 0.70}}
    repository.places = {PARENT: PLACE}
    priority = {p['h3']: p for p in client.get(URL).json()['alerts']['priority']}
    assert priority[PARENT]['place'] == PLACE and priority[other]['place'] is None
