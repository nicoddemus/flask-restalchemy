from flask_restful import Api as RestfulApi
from marshmallow_sqlalchemy import ModelSchema

from flask_rest_orm.resources.resources import CollectionResource, ItemResource, CollectionRelationResource, \
    ItemRelationResource


class Api(object):

    def __init__(self, app=None, prefix='', errors=None, request_decorators=None):
        self.restful_api = RestfulApi(app=app, prefix=prefix, decorators=request_decorators,
                                      default_mediatype='application/json', errors=errors)
        self._db = None
        if app:
            self.init_app(app)

    def add_model(self, model, url=None, serializer=None, request_decorators=None,
                  collection_decorators=None):
        """
        Create API endpoints for the given SQLAlchemy declarative class.

        :param class model: the SQLAlchemy declarative class

        :param string url: one or more url routes to match for the resource, standard
             flask routing rules apply. Defaults to model name in lower case.

        :param ModelSchema serializer: Marshmallow schema for serialization. If `None`, a default serializer will be
            created.

        :param list|dict request_decorators: decorators to be applied to HTTP methods. Could be a list of decorators
            or a dict mapping HTTP method types to a list of decorators (dict keys should be 'get', 'post' or 'put').
            See https://flask-restful.readthedocs.io/en/latest/extending.html#resource-method-decorators for more
            details.

        :param list|dict collection_decorators: decorators to be applied to HTTP methods for collections. It defaults to
            request_decorators value.
        """
        restful = self.restful_api
        collection_name = model.__tablename__
        if not serializer:
            serializer = self.create_default_serializer(model)()
        url =  url or '/' + collection_name.lower()

        if not request_decorators:
            request_decorators = []
        if not collection_decorators:
            collection_decorators = request_decorators

        class _CollectionResource(CollectionResource):
            method_decorators = collection_decorators

        class _ItemResource(ItemResource):
            method_decorators = request_decorators

        restful.add_resource(
            _CollectionResource,
            url,
            endpoint=collection_name + '-list',
            resource_class_args=(model, serializer, self.get_db_session),
        )
        restful.add_resource(
            _ItemResource,
            url + '/<id>',
            endpoint=collection_name,
            resource_class_args=(model, serializer, self.get_db_session)
        )


    def add_relation(self, model, relation_fk, related_model, url_rule=None, serializer=None, request_decorators=None,
              collection_decorators=None):
        model_collection_name = model.__tablename__.lower()
        related_collection_name = related_model.__tablename__.lower()
        endpoint_name = '{}-{}-relation'.format(model_collection_name, related_collection_name)
        if not serializer:
            serializer = self.create_default_serializer(model)()
        if url_rule:
            assert '<relation_id>' in url_rule
        else:
            url_rule = '/{}/<relation_id>/{}'.format(related_collection_name, model_collection_name)

        if not request_decorators:
            request_decorators = []
        if not collection_decorators:
            collection_decorators = request_decorators

        class _CollectionRelationResource(CollectionRelationResource):
            method_decorators = collection_decorators

        class _ItemRelationResource(ItemRelationResource):
            method_decorators = collection_decorators

        self._add_resources(
            _ItemRelationResource,
            _CollectionRelationResource,
            url_rule,
            endpoint_name,
            resource_init_args=(model, relation_fk, related_model, serializer, self.get_db_session),
        )

    def _add_resources(self, item_resource, collection_resource, url_rule, endpoint_prefix, resource_init_args):
        restful = self.restful_api
        restful.add_resource(
            item_resource,
            url_rule + '/<id>',
            endpoint=endpoint_prefix,
            resource_class_args=resource_init_args,
        )
        restful.add_resource(
            collection_resource,
            url_rule,
            endpoint=endpoint_prefix + '-list',
            resource_class_args=resource_init_args,
        )

    @staticmethod
    def create_default_serializer(model_class):
        """
        Create a default serializer for the given SQLAlchemy declarative class. Recipe based on
        https://marshmallow-sqlalchemy.readthedocs.io/en/latest/recipes.html#automatically-generating-schemas-for-sqlalchemy-models

        :param model_class: the SQLAlchemy mapped class

        :rtype: class
        """
        class Meta(object):
            model = model_class
            include_fk = True

        schema_class_name = '{}Schema'.format(model_class.__name__)
        schema_class = type(
            schema_class_name,
            (ModelSchema,),
            {'Meta': Meta}
        )
        return schema_class

    def init_app(self, app):
        self.restful_api.init_app(app)
        self._db = app.extensions['sqlalchemy'].db


    def get_db_session(self):
        return self._db.session
