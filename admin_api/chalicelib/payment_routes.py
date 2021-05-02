from chalice import Blueprint, Response
from . import app, authorizer
from .dynamodb import get_org_table
from .decorator import check_org_permission, check_json_body
from decimal import Decimal
import os
import stripe
import time

payment_routes = Blueprint(__name__)

stripe.api_key = os.environ.get('STRIPE_SK')


@payment_routes.route('/', methods=['GET'], cors=True, authorizer=authorizer)
@check_org_permission('admin')
def get_payment_customer(org):
    org_info = get_org_table().get_item(Key={'name': org})
    if 'Item' not in org_info:
        return Response(body={'error': 'not found'}, status_code=404)

    if 'payment' in org_info['Item']:
        data = org_info['Item']['payment']
        customer = stripe.Customer.retrieve(data['id'])
        pm_id = customer['invoice_settings']['default_payment_method']
        pm = stripe.PaymentMethod.retrieve(pm_id)

        return {'id': data['id'], 'name': customer['name'], 'email': customer['email'], 'payment_method': pm}

    return None


@payment_routes.route('/', methods=['PUT'], cors=True, authorizer=authorizer)
@check_org_permission('admin')
@check_json_body({
    'email': {'type': 'string', 'required': True, 'empty': False},
    'name': {'type': 'string', 'required': True, 'empty': False},
    'payment_method': {'type': 'string', 'required': True, 'empty': False}
})
def put_payment_customer(org):
    org_info = get_org_table().get_item(Key={'name': org})
    if 'Item' not in org_info:
        return Response(body={'error': 'not found'}, status_code=404)

    request = app.current_request
    body = request.json_body

    if 'payment' in org_info['Item']:
        data = org_info['Item']['payment']
        stripe.PaymentMethod.attach(body['payment_method'], customer=data['id'])
        customer = stripe.Customer.modify(
            data['id'],
            email=body['email'],
            name=body['name'],
            invoice_settings={'default_payment_method': body['payment_method']}
        )
    else:
        customer = stripe.Customer.create(
            email=body['email'],
            name=body['name'],
            metadata={'org': org},
            payment_method=body['payment_method'],
            invoice_settings={'default_payment_method': body['payment_method']}
        )

    ts = Decimal(time.time())
    org_info['Item']['updated_at'] = ts
    org_info['Item']['payment'] = customer
    get_org_table().put_item(Item=org_info['Item'])

    pm_id = customer['invoice_settings']['default_payment_method']
    pm = stripe.PaymentMethod.retrieve(pm_id)

    return {'id': customer['id'], 'name': body['name'], 'email': body['email'], 'payment_method': pm}
