from flask import Blueprint
from flask_restful import Api

api_bp: Blueprint = Blueprint('api', __name__, url_prefix='/api')
api: Api = Api(api_bp)
