import pytest
from flask import json

from flask_restalchemy import Api
from flask_restalchemy.tests.sample_model import Employee, Company, EmployeeSerializer, Department


@pytest.fixture(autouse=True)
def create_test_sample(db_session):
    company1 = Company(id=1, name='Protoss')
    company2 = Company(id=3, name='Terrans')
    emp1 = Employee(id=9, firstname='Jim', lastname='Raynor', company=company2)
    emp2 = Employee(id=3, firstname='Sarah', lastname='Kerrigan', company=company2)
    dept1 = Department(name='Marines')
    dept2 = Department(name='Heroes')
    emp1.departments.append(dept1)
    emp1.departments.append(dept2)

    db_session.add(company1)
    db_session.add(company2)
    db_session.add(dept1)
    db_session.add(dept2)
    db_session.add(emp1)
    db_session.add(emp2)
    db_session.commit()

@pytest.fixture(autouse=True)
def sample_api(flask_app):
    api = Api(flask_app)
    api.add_model(Company)
    api.add_model(Employee)
    api.add_relation(Company.employees, serializer_class=EmployeeSerializer)
    api.add_property(Employee, Employee, 'colleagues', serializer_class=EmployeeSerializer)
    api.add_relation(Employee.departments)
    return api

def test_get_collection(client):
    resp = client.get('/company/3/employees')
    assert resp.status_code == 200
    assert len(resp.parsed_data) == 2
    sarah = resp.parsed_data[0]
    assert sarah['firstname'] == 'Sarah'
    assert sarah['lastname'] == 'Kerrigan'
    jim = resp.parsed_data[1]
    assert jim['firstname'] == 'Jim'
    assert jim['lastname'] == 'Raynor'

def test_post(client):
    resp = client.post('/company/3/employees', data={'firstname': 'Tychus', 'lastname': 'Findlay'})
    assert resp.status_code == 201
    empl_id = resp.parsed_data['id']
    thychus = Employee.query.get(empl_id)
    assert thychus.company_name == 'Terrans'

def test_post_append_existent(client):
    resp = client.post('/employee', data={'firstname': 'Tychus', 'lastname': 'Findlay'})
    assert resp.status_code == 201
    empl_id = resp.parsed_data['id']
    thychus = Employee.query.get(empl_id)
    assert thychus.company_name is None

    resp = client.post('/company/3/employees', data={'id': empl_id})
    assert resp.status_code == 200

    thychus = Employee.query.get(empl_id)
    assert thychus.company_name == 'Terrans'

    resp = client.post('/company/3/employees', data={'id': 1000})
    assert resp.status_code == 404

def test_get(client):
    resp = client.get('/company/3/employees/9')
    assert resp.status_code == 200
    obtained = resp.parsed_data
    assert obtained['firstname'] == 'Jim'
    assert obtained['lastname'] == 'Raynor'
    assert obtained['company_name'] == 'Terrans'
    # Query a valid resource ID, but with a wrong related ID
    resp = client.get('/company/4/employees/9')
    assert resp.status_code == 404

def test_put(client):
    new_name = 'Jimmy'
    resp = client.put('/company/3/employees/9', data={'firstname': new_name})
    assert resp.status_code == 200
    jim = Employee.query.get(9)
    assert jim.firstname == new_name

def test_delete(client):
    jim = Employee.query.get(9)
    assert jim is not None

    resp = client.delete('/company/3/employees/9')
    assert resp.status_code == 204


def test_delete_on_relation_with_secondary(client):
    jim = Employee.query.get(9)
    assert jim is not None
    assert len(jim.departments) > 0
    dep = jim.departments[0]

    sarah = Employee.query.get(3)
    assert jim is not None
    assert dep not in sarah.departments

    resp = client.get('/employee/3/departments')
    assert resp.status_code == 200

    resp = client.delete('/employee/3/departments/' + str(dep.id))
    assert resp.status_code == 404

    resp = client.delete('/employee/9/departments/'+str(dep.id))
    assert resp.status_code == 204


def test_property(client):
    resp = client.get('/employee/9/colleagues')
    assert resp.status_code == 200
    assert len(resp.parsed_data) == 2
    assert resp.parsed_data[0]['firstname'] == 'Sarah'
    assert resp.parsed_data[1]['firstname'] == 'Jim'

    resp = client.post('/employee/9/colleagues')
    assert resp.status_code == 405


def test_property_pagination(client):

    for i in range(20):
        client.post('/company/3/employees', data={'firstname': 'Jimmy {}'.format(i)})

    response = client.get('/employee/9/colleagues?order_by=id&limit=5')
    assert response.status_code == 200
    assert len(response.parsed_data) == 5
    assert response.parsed_data[0]['firstname'] == 'Sarah'

    response = client.get(
        '/employee/9/colleagues?filter={}'.format(json.dumps({"firstname": {"eq": "Sarah"}})))
    assert response.status_code == 200
    dataList = response.parsed_data
    assert len(dataList) == 1
    assert 'firstname' in dataList[0]
    assert dataList[0]['firstname'] == 'Sarah'

    response = client.get('/employee/9/colleagues?page=1&per_page=10')
    assert response.status_code == 200
    dataList = response.parsed_data
    assert len(dataList.get('results')) == 10
