# -*- coding: utf-8 -*-
from copy import deepcopy
from requests import Session
from datetime import timedelta

from openregistry.lots.core.tests.base import PrefixedRequestClass, DumpsTestAppwebtest
from openregistry.lots.loki.tests.base import BaseLotWebTest
from openregistry.lots.loki.tests.json_data import (
    test_loki_lot_data,
    auction_english_data,
    auction_second_english_data
)
from openregistry.lots.loki.models import Lot, Period
from openregistry.lots.loki.tests.blanks.lot_blanks import add_decisions, add_cancellationDetails_document
from openregistry.lots.core.utils import get_now, calculate_business_date
from openprocurement.api.config import DS
from openprocurement.api.tests.base import test_config_data
DumpsTestAppwebtest.hostname = "lb.api-sandbox.registry.ea2.openprocurement.net"
SESSION = Session()


class LotResourceTest(BaseLotWebTest):

    def setUp(self):
        super(LotResourceTest, self).setUp()
        self.app = DumpsTestAppwebtest(
            "config:tests.ini", relative_to=self.relative_to)
        self.app.RequestClass = PrefixedRequestClass
        self.app.authorization = ('Basic', ('broker', ''))
        self.couchdb_server = self.app.app.registry.couchdb_server
        self.db = self.app.app.registry.db
        self.app.app.registry.docservice_url = 'http://localhost'
        ds_config = deepcopy(test_config_data['config']['ds'])
        docserv = DS(ds_config)
        self.app.app.registry.docservice_key = dockey = docserv.signer
        self.app.app.registry.keyring = docserv.init_keyring(dockey)
        self._srequest = SESSION.request
        self.app.app.registry.use_docservice=True
        self.lot_model = Lot

    def from_initial_to_decisions(self):
        request_path = '/?opt_pretty=1'

        response = self.app.post_json(request_path, {"data": self.initial_data})
        self.assertEqual(response.status, '201 Created')

        lot = response.json['data']
        lot_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        response = self.app.get('/{}'.format(lot_id))
        self.assertEqual(response.status, '200 OK')

        response = self.app.get('/{}/auctions'.format(lot_id))
        auctions = sorted(response.json['data'], key=lambda a: a['tenderAttempts'])
        english = auctions[0]
        second_english = auctions[1]
        access_header = {'X-Access-Token': str(owner_token)}

        # Switch to 'composing'
        response = self.app.patch_json('/{}?acc_token={}'.format(lot_id, owner_token),
                                       {'data': {"status": 'composing'}})
        self.assertEqual(response.status, '200 OK')

        # Compose lot with first english data
        response = self.app.patch_json(
            '/{}/auctions/{}'.format(lot_id, english['id']),
            params={'data': auction_english_data}, headers=access_header)
        self.assertEqual(response.status, '200 OK')

        # Compose lot with second english data
        response = self.app.patch_json(
            '/{}/auctions/{}'.format(lot_id, second_english['id']),
            params={'data': auction_second_english_data}, headers=access_header)
        self.assertEqual(response.status, '200 OK')

        # Switch to 'verification'
        response = self.app.patch_json('/{}?acc_token={}'.format(lot_id, owner_token),
                                       {'data': {"status": 'verification'}})
        self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('concierge', ''))

        add_decisions(self, lot)
        return lot, lot_id, owner_token

    def test_docs_tutorial(self):
        request_path = '/?opt_pretty=1'

        # Exploring basic rules
        #
        with open('docs/source/tutorial/lot-listing.http', 'w') as self.app.file_obj:
            response = self.app.get(request_path)
            self.assertEqual(response.status, '200 OK')
            self.app.file_obj.write("\n")

        with open('docs/source/tutorial/lot-post-attempt.http', 'w') as self.app.file_obj:
            response = self.app.post(request_path, 'data', status=415)
            self.assertEqual(response.status, '415 Unsupported Media Type')

        with open('docs/source/tutorial/lot-post-attempt-json.http', 'w') as self.app.file_obj:
            response = self.app.post(
                request_path, 'data', content_type='application/json', status=422)
            self.assertEqual(response.status, '422 Unprocessable Entity')

        # Creating lot in draft status
        #
        with open('docs/source/tutorial/lot-post-2pc.http', 'w') as self.app.file_obj:
            response = self.app.post_json(request_path, {"data": self.initial_data})
            self.assertEqual(response.status, '201 Created')

        lot = response.json['data']
        lot_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        with open('docs/source/tutorial/blank-lot-view.http', 'w') as self.app.file_obj:
            response = self.app.get('/{}'.format(lot_id))
            self.assertEqual(response.status, '200 OK')

        response = self.app.get('/{}/auctions'.format(lot_id))
        auctions = sorted(response.json['data'], key=lambda a: a['tenderAttempts'])
        english = auctions[0]
        second_english = auctions[1]
        access_header = {'X-Access-Token': str(owner_token)}

        # Switch to 'composing'
        #
        with open('docs/source/tutorial/lot-to-composing.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}?acc_token={}'.format(lot_id, owner_token),
                                           {'data': {"status": 'composing'}})
            self.assertEqual(response.status, '200 OK')

        # Compose lot with first english data
        #
        with open('docs/source/tutorial/compose_lot_patch_1.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/{}/auctions/{}'.format(lot_id, english['id']),
                params={'data': auction_english_data}, headers=access_header)
            self.assertEqual(response.status, '200 OK')

        # Compose lot with second english data
        #
        with open('docs/source/tutorial/compose_lot_patch_2.http', 'w') as self.app.file_obj:
            response = self.app.patch_json(
                '/{}/auctions/{}'.format(lot_id, second_english['id']),
                params={'data': auction_second_english_data}, headers=access_header)
            self.assertEqual(response.status, '200 OK')

        # Switch to 'verification'
        #
        with open('docs/source/tutorial/lot-to-varification.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}?acc_token={}'.format(lot_id, owner_token),
                                           {'data': {"status": 'verification'}})
            self.assertEqual(response.status, '200 OK')

        # Hack for update_after
        #
        self.app.get(request_path)
        #

        with open('docs/source/tutorial/initial-lot-listing.http', 'w') as self.app.file_obj:
            response = self.app.get(request_path)
            self.assertEqual(response.status, '200 OK')

        with open('docs/source/tutorial/create-second-lot.http', 'w') as self.app.file_obj:
            response = self.app.post_json(request_path, {"data": self.initial_data})
            self.assertEqual(response.status, '201 Created')

        second_lot_id = response.json['data']['id']
        second_owner_token = response.json['access']['token']

        response = self.app.get('/{}/auctions'.format(second_lot_id))
        auctions = sorted(response.json['data'], key=lambda a: a['tenderAttempts'])
        english = auctions[0]
        second_english = auctions[1]
        second_access_header = {'X-Access-Token': str(second_owner_token)}

        # Switch to 'composing'
        #
        with open('docs/source/tutorial/second-lot-to-composing.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}?acc_token={}'.format(second_lot_id, second_owner_token),
                                           {'data': {"status": 'composing'}})
            self.assertEqual(response.status, '200 OK')

        # Hack for update_after
        #
        self.app.get(request_path)
        #

        with open('docs/source/tutorial/listing-with-some-lots.http', 'w') as self.app.file_obj:
            response = self.app.get(request_path)
            import ipdb; ipdb.set_trace()
            self.assertEqual(response.status, '200 OK')

        # Modifying lot
        #
        with open('docs/source/tutorial/patch-lot.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}?acc_token={}'.format(second_lot_id, second_owner_token), {'data':
                {
                    "description": "Lot description modified"
                }
            })
            self.assertEqual(response.status, '200 OK')

        self.app.get(request_path)
        with open('docs/source/tutorial/lot-listing-after-patch.http', 'w') as self.app.file_obj:
            response = self.app.get(request_path)
            self.assertEqual(response.status, '200 OK')

        # Posting decisions to the first lot to be able to switch to pending
        self.app.authorization = ('Basic', ('concierge', ''))

        add_decisions(self, lot)
 
        # Switch first lot to 'pending'
        #
        with open('docs/source/tutorial/lot-patch-2pc.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}?acc_token={}'.format(lot_id, owner_token),
                                           {'data': {"status": 'pending'}})
            self.assertEqual(response.status, '200 OK')

        # Switch first lot to 'pending.deleted'
        #

        self.app.authorization = ('Basic', ('broker', ''))
        access_header = {'X-Access-Token': str(owner_token)}
        with open('docs/source/tutorial/add_cancellation_docs.hhtp', 'w') as self.app.file_obj:
            add_cancellationDetails_document(self, lot, access_header)
            
        with open('docs/source/tutorial/lot-delete-2pc.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}?acc_token={}'.format(lot_id, owner_token),
                                           {'data': {"status": 'pending.deleted'}})
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker', ''))

 
    def test_docs_tutorial_with_concierge(self):

        ### Switch to invalid workflow ###

        lot, lot_id, owner_token = self.from_initial_to_decisions()

        self.app.authorization = ('Basic', ('concierge', ''))
        with open('docs/source/tutorial/switch-lot-to-invalid.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}'.format(lot_id),
                                           params={'data': {"status": 'invalid'}})
            self.assertEqual(response.status, '200 OK')

        ### Switch to deleted workflow ###
        self.app.authorization = ('Basic', ('broker', ''))
        lot, lot_id, owner_token = self.from_initial_to_decisions()
        access_header = {'X-Access-Token': str(owner_token)}

          # switch lot to 'pending'
        with open('docs/source/tutorial/switch-lot-to-pending.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}?acc_token={}'.format(lot_id, owner_token),
                                           {'data': {"status": 'pending'}})
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('broker', ''))
        add_cancellationDetails_document(self, lot, access_header)

          # switch lot to 'deleted'
        with open('docs/source/tutorial/lot-delete-3pc.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}?acc_token={}'.format(lot_id, owner_token),
                                           {'data': {"status": 'pending.deleted'}})
            self.assertEqual(response.status, '200 OK')

        ### Switch to pending.dissolution workflow ###

        self.app.authorization = ('Basic', ('broker', ''))
        lot, lot_id, owner_token = self.from_initial_to_decisions()
        access_header = {'X-Access-Token': str(owner_token)}

          # switch lot to 'pending'
        response = self.app.patch_json('/{}?acc_token={}'.format(lot_id, owner_token),
                                       {'data': {"status": 'pending'}})
        self.assertEqual(response.status, '200 OK')

        rectificationPeriod = Period()
        rectificationPeriod.startDate = get_now() - timedelta(3)
        rectificationPeriod.endDate = calculate_business_date(rectificationPeriod.startDate,
                                                              timedelta(1), None)
          # change rectification period in db
        fromdb = self.db.get(lot['id'])
        fromdb = self.lot_model(fromdb)

        fromdb.status = 'pending'
        fromdb.decisions = [
            {
                'decisionDate': get_now().isoformat(),
                'decisionID': 'decisionAssetID'
            },
            {
                'decisionDate': get_now().isoformat(),
                'decisionID': 'decisionAssetID'
            }
        ]
        fromdb.title = 'title'
        fromdb.rectificationPeriod = rectificationPeriod
        fromdb = fromdb.store(self.db)
        lot = fromdb
        self.assertEqual(fromdb.id, lot['id'])

          # switch lot to 'active.salable'
        response = self.app.get('/{}'.format(lot['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['id'], lot['id'])

        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/{}'.format(lot['id']),
                                       params={'data': {'title': ' PATCHED'}})
        self.assertNotEqual(response.json['data']['title'], 'PATCHED')
        self.assertEqual(lot['title'], response.json['data']['title'])
        self.assertEqual(response.json['data']['status'], 'active.salable')

        with open('docs/source/tutorial/concierge-patched-lot-to-active.salable.http', 'w') as self.app.file_obj:
            response = self.app.get('/{}'.format(lot_id))
            self.assertEqual(response.status, '200 OK')

          # switch lot to 'active.auction'
        self.app.authorization = ('Basic', ('concierge', ''))

        with open('docs/source/tutorial/switch-lot-active.auction.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}'.format(lot_id),
                                           {'data': {"status": 'active.auction'}})
            self.assertEqual(response.status, '200 OK')

        self.app.authorization = ('Basic', ('convoy', ''))

        with open('docs/source/tutorial/switch-lot-active.contracting.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}'.format(lot_id),
                                           {'data': {"status": 'active.contracting'}})
            self.assertEqual(response.status, '200 OK')

          # switch to 'pending.dissolution'
        with open('docs/source/tutorial/patch-lot-to-pending.dissolution.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}'.format(lot_id),
                                           {'data': {"status": 'pending.dissolution'}})
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(response.json['data']['status'], 'pending.dissolution')

        self.app.authorization = ('Basic', ('concierge', ''))

          # Switch to 'dissolved'

        with open('docs/source/tutorial/patch-lot-to-dissolved.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}'.format(lot_id),
                                           {'data': {"status": 'dissolved'}})
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(response.json['data']['status'], 'dissolved')

        ### Switch to sold workflow ###

        self.app.authorization = ('Basic', ('broker', ''))

        lot, lot_id, owner_token = self.from_initial_to_decisions()

          # switch lot to 'pending'
        response = self.app.patch_json('/{}?acc_token={}'.format(lot_id, owner_token),
                                       {'data': {"status": 'pending'}})
        self.assertEqual(response.status, '200 OK')

        rectificationPeriod = Period()
        rectificationPeriod.startDate = get_now() - timedelta(3)
        rectificationPeriod.endDate = calculate_business_date(rectificationPeriod.startDate,
                                                              timedelta(1), None)
          # change rectification period in db
        fromdb = self.db.get(lot['id'])
        fromdb = self.lot_model(fromdb)

        fromdb.status = 'pending'
        fromdb.decisions = [
            {
                'decisionDate': get_now().isoformat(),
                'decisionID': 'decisionAssetID'
            },
            {
                'decisionDate': get_now().isoformat(),
                'decisionID': 'decisionAssetID'
            }
        ]
        fromdb.title = 'title'
        fromdb.rectificationPeriod = rectificationPeriod
        fromdb = fromdb.store(self.db)
        lot = fromdb
        self.assertEqual(fromdb.id, lot['id'])

          # switch lot to 'active.salable'
        response = self.app.get('/{}'.format(lot['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['id'], lot['id'])

        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/{}'.format(lot['id']),
                                       params={'data': {'title': ' PATCHED'}})
        self.assertNotEqual(response.json['data']['title'], 'PATCHED')
        self.assertEqual(lot['title'], response.json['data']['title'])
        self.assertEqual(response.json['data']['status'], 'active.salable')

        response = self.app.get('/{}'.format(lot_id))
        self.assertEqual(response.status, '200 OK')

          # switch lot to 'active.auction'
        self.app.authorization = ('Basic', ('concierge', ''))

        response = self.app.patch_json('/{}'.format(lot_id),
                                       {'data': {"status": 'active.auction'}})
        self.assertEqual(response.status, '200 OK')


          # switch to 'active.contracting'
        self.app.authorization = ('Basic', ('convoy', ''))

        response = self.app.patch_json('/{}'.format(lot_id),
                                       {'data': {"status": 'active.contracting'}})
        self.assertEqual(response.status, '200 OK')

          # switch to 'pending.sold'
        with open('docs/source/tutorial/switch-lot-to-pending.sold.http', 'w') as self.app.file_obj:
            response = self.app.patch_json('/{}'.format(lot_id),
                                           {'data': {"status": 'pending.sold'}})
            self.assertEqual(response.status, '200 OK')

          # switch to 'sold'
        with open('docs/source/tutorial/switch-lot-to-sold.http', 'w') as self.app.file_obj:
            self.app.authorization = ('Basic', ('concierge', ''))
            response = self.app.patch_json('/{}'.format(lot_id),
                                           {'data': {"status": 'sold'}})
            self.assertEqual(response.status, '200 OK')