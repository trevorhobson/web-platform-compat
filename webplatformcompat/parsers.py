from rest_framework_json_api.parsers import JsonApiParser \
    as BaseJsonApiParser
from rest_framework_json_api.utils import snakecase


class JsonApiParser(BaseJsonApiParser):
    def model_to_resource_type(self, model):
        if model:
            return snakecase(model._meta.verbose_name_plural)
        else:
            return 'data'