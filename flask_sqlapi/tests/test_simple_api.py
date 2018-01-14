from datetime import datetime

import pytest
from marshmallow import fields
from marshmallow_sqlalchemy import ModelSchema

from flask_sqlapi.resources import Api
from flask_sqlapi.tests.sample_model import Employee, db, Company, Address, Address


class AddressSerializer(ModelSchema):
    class Meta:
        model = Address


class EmployeeSerializer(ModelSchema):
    class Meta:
        model = Employee

    password = fields.Str(load_only=True)
    created_at = fields.DateTime(dump_only=True)
    company_name = fields.Str(dump_only=True)
    address = fields.Nested(AddressSerializer)


@pytest.fixture()
def sample_api(flask_app):
    api = Api(flask_app)
    api.add_model(Company)
    api.add_model(Employee, serializer=EmployeeSerializer())
    return api


@pytest.fixture(autouse=True)
def register_model_and_api(db_session, sample_api):
    company = Company(id=5, name='Terrans')
    emp1 = Employee(id=1, firstname='Jim', lastname='Raynor', company=company)
    emp2 = Employee(id=2, firstname='Sarah', lastname='Kerrigan', company=company)

    addr1 = Address(street="5 Av", number="943", city="Tarsonis")
    emp1.address = addr1

    db_session.add(company)
    db_session.add(emp1)
    db_session.add(emp2)
    db_session.commit()


# noinspection PyShadowingNames
def test_get(client):
    resp = client.get('/employee/1')
    assert resp.status_code == 200
    expected_employee = Employee.query.get(1)
    serialized = resp.parsed_data
    assert serialized['firstname'] == expected_employee.firstname
    assert serialized['lastname'] == expected_employee.lastname
    assert serialized['created_at'] == '2000-01-01T00:00:00+00:00'
    assert 'password' not in serialized
    assert serialized['company'] == expected_employee.company_id
    assert serialized['company_name'] == Company.query.get(expected_employee.company_id).name

    assert serialized['address'] == AddressSerializer().dump(expected_employee.address).data


# noinspection PyShadowingNames
def test_get_collection(client):
    resp = client.get('/employee')
    assert resp.status_code == 200
    assert len(resp.parsed_data) == 2
    for i, expected_employee in enumerate(Employee.query.all()):
        serialized = resp.parsed_data[i]
        assert serialized['firstname'] == expected_employee.firstname
        assert serialized['lastname'] == expected_employee.lastname
        assert 'password' not in serialized


def test_post(client):
    post_data = {
        'id': 3,
        'firstname': 'Tychus',
        'lastname': 'Findlay',
        'created_at': '2002-02-02T00:00'
    }
    resp = client.post('/employee', data=post_data)
    assert resp.status_code == 201
    emp3 = Employee.query.get(3)
    assert emp3.id == 3
    assert emp3.firstname == 'Tychus'
    assert emp3.lastname == 'Findlay'
    assert emp3.created_at == datetime(2000, 1, 1)


def test_post_default_serializer(client):
    resp = client.post('/company', data={'name': 'Mangsk Corp', })
    assert resp.status_code == 201


def test_put(client):
    resp = client.put('/employee/2', data={'id': 2, 'firstname': 'Jimmy'})
    assert resp.status_code == 200
    emp3 = Employee.query.get(2)
    assert emp3.firstname == 'Jimmy'
