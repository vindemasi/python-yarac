# test_client.py - python RabbitMQ api client test suite
#
# Copyright (c) 2016 Vincenzo Demasi <vindemasi@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import logging
from unittest import TestCase
from os.path import dirname, join

from vcr import VCR

import yarac

logging.basicConfig()
logger = logging.getLogger("vcr")
logger.setLevel(logging.INFO)

recorder = VCR(
    cassette_library_dir=join(dirname(__file__), "fixtures"),
    serializer="yaml",
    path_transformer=VCR.ensure_suffix('.yaml'),
    decode_compressed_response=True,
    record_mode="once"
)


class TestClient(TestCase):
    client = yarac.Client("http://guest:guest@localhost:15672/api")

    def test_request_unsupported_method(self):
        with self.assertRaises(yarac.ParameterError):
            self.client.request("head", self.client.build_url("/overview"))

    @recorder.use_cassette
    def test_request_3xx_response(self):
        with self.assertRaises(yarac.RedirectionError):
            self.client.request("get", self.client.build_url("/overview"))

    @recorder.use_cassette
    def test_request_4xx_response(self):
        with self.assertRaises(yarac.BadRequestError):
            self.client.request("post", self.client.build_url("/overview"))

    @recorder.use_cassette
    def test_request_5xx_response(self):
        with self.assertRaises(yarac.ServerError):
            self.client.request("get", self.client.build_url("/overview"))

    @recorder.use_cassette
    def test_request_unhandled_status_response(self):
        with self.assertRaises(yarac.RequestError):
            self.client.request("get", self.client.build_url("/overview"))

    @recorder.use_cassette
    def test_get_overview(self):
        self.client.get_overview()

    @recorder.use_cassette
    def test_get_cluster_name(self):
        self.client.get_cluster_name()

    @recorder.use_cassette(decode_compressed_response=False)
    def test_set_cluster_name(self):
        self.client.set_cluster_name("rabbit@localhost")

    @recorder.use_cassette
    def test_list_cluster_nodes(self):
        self.client.list_cluster_nodes()

    @recorder.use_cassette
    def test_get_cluster_node(self):
        self.client.get_cluster_node("rabbit@katorz", memory=True, binary=True)

    @recorder.use_cassette
    def test_list_management_extensions(self):
        self.client.list_management_extensions()

    @recorder.use_cassette
    def test_export_server_definitions(self):
        self.client.export_server_definitions()

    @recorder.use_cassette(decode_compressed_response=False)
    def test_merge_server_definitions(self):
        self.client.merge_server_definitions({})

    @recorder.use_cassette
    def test_export_vhost_definitions(self):
        self.client.export_vhost_definitions()

    @recorder.use_cassette(decode_compressed_response=False)
    def test_merge_vhost_definitions(self):
        self.client.merge_vhost_definitions({})

    @recorder.use_cassette
    def test_list_connections(self):
        self.client.list_connections()

    @recorder.use_cassette
    def test_list_vhost_connections(self):
        self.client.list_vhost_connections()

    @recorder.use_cassette
    def test_get_connection(self):
        self.client.get_connection("[::1]:49922 -> [::1]:5672")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_drop_connection(self):
        self.client.drop_connection("127.0.0.1:58162 -> 127.0.0.1:5672", reason="test drop connection")

    @recorder.use_cassette
    def test_list_connection_channels(self):
        self.client.list_connection_channels("[::1]:49944 -> [::1]:5672")

    @recorder.use_cassette
    def test_list_channels(self):
        self.client.list_channels()

    @recorder.use_cassette
    def test_list_vhost_channels(self):
        self.client.list_vhost_channels()

    @recorder.use_cassette
    def test_get_channel(self):
        self.client.get_channel("[::1]:49944 -> [::1]:5672 (1)")

    @recorder.use_cassette
    def test_list_consumers(self):
        self.client.list_consumers()

    @recorder.use_cassette
    def test_list_vhost_consumers(self):
        self.client.list_vhost_consumers()

    @recorder.use_cassette
    def test_list_exchanges(self):
        self.client.list_exchanges()

    @recorder.use_cassette
    def test_list_vhost_exchanges(self):
        self.client.list_vhost_exchanges()

    @recorder.use_cassette
    def test_get_exchange(self):
        self.client.get_exchange("amq.direct")

    @recorder.use_cassette
    def test_get_default_exchange(self):
        self.client.get_exchange("")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_declare_exchange(self):
        self.client.declare_exchange("test-exchange", type="direct")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_delete_exchange(self):
        self.client.delete_exchange("test-exchange", unused_only=True)

    @recorder.use_cassette
    def test_list_exchange_outgoing_bindings(self):
        self.client.list_exchange_outgoing_bindings("test-exchange")

    @recorder.use_cassette
    def test_list_exchange_incoming_bindings(self):
        self.client.list_exchange_incoming_bindings("test-other-exchange")

    @recorder.use_cassette
    def test_publish_message(self):
        self.client.publish_message("test-exchange", payload="Hello", routing_key="test.route")

    @recorder.use_cassette
    def test_list_queues(self):
        self.client.list_queues()

    @recorder.use_cassette
    def test_list_vhost_queues(self):
        self.client.list_vhost_queues()

    @recorder.use_cassette
    def test_get_queue(self):
        self.client.get_queue("test-queue")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_declare_queue(self):
        self.client.declare_queue("test-queue", arguments={"test-argument": "foo"}, node="rabbit@localhost")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_delete_queue(self):
        self.client.delete_queue("test-queue")

    @recorder.use_cassette
    def test_list_queue_bindings(self):
        self.client.list_queue_bindings("test-queue")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_purge_queue(self):
        self.client.purge_queue("test-queue")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_do_queue_action(self):
        self.client.do_queue_action("test-queue", "sync")

    @recorder.use_cassette
    def test_get_messages(self):
        self.client.get_messages("test-queue", truncate=1000)

    @recorder.use_cassette
    def test_list_bindings(self):
        self.client.list_bindings()

    @recorder.use_cassette
    def test_list_vhost_bindings(self):
        self.client.list_vhost_bindings()

    @recorder.use_cassette
    def test_list_exchange_to_queue_bindings(self):
        self.client.list_exchange_to_queue_bindings("test-exchange", "test-queue")

    @recorder.use_cassette
    def test_get_exchange_to_queue_binding(self):
        self.client.get_exchange_to_queue_binding("test-exchange", "test-queue", "test.route")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_declare_exchange_to_queue_binding(self):
        self.client.declare_exchange_to_queue_binding("test-exchange", "test-queue", routing_key="foo")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_delete_exchange_to_queue_binding(self):
        self.client.delete_exchange_to_queue_binding("test-exchange", "test-queue", "test.route")

    @recorder.use_cassette
    def test_list_exchange_to_exchange_bindings(self):
        self.client.list_exchange_to_exchange_bindings("test-exchange", "test-other-exchange")

    @recorder.use_cassette
    def test_get_exchange_to_exchange_binding(self):
        self.client.get_exchange_to_exchange_binding("test-exchange", "test-other-exchange", "other%2Croute")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_declare_exchange_to_exchange_binding(self):
        self.client.declare_exchange_to_exchange_binding("test-exchange", "test-other-exchange", routing_key="bar")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_delete_exchange_to_exchange_binding(self):
        self.client.delete_exchange_to_exchange_binding("test-exchange", "test-other-exchange", "other%2Croute")

    @recorder.use_cassette
    def test_list_virtual_hosts(self):
        self.client.list_virtual_hosts()

    @recorder.use_cassette
    def test_get_virtual_host(self):
        self.client.get_virtual_host(vhost="test-vhost")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_declare_virtual_host(self):
        self.client.declare_virtual_host("test-vhost")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_delete_virtual_host(self):
        self.client.delete_virtual_host("test-vhost")

    @recorder.use_cassette
    def test_list_vhost_permissions(self):
        self.client.list_vhost_permissions()

    @recorder.use_cassette
    def test_list_users(self):
        self.client.list_users()

    @recorder.use_cassette
    def test_get_user(self):
        self.client.get_user("test-user")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_set_user(self):
        self.client.set_user("test-user", password="password", tags="")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_set_user_with_password_hash(self):
        self.client.set_user("test-user", password_hash="NXIwiPGb6FSWVh7J7zuszrHc9mOX8sbViT55j56H8iJ4w1/j", tags="")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_delete_user(self):
        self.client.delete_user("test-user")

    @recorder.use_cassette
    def test_list_user_permissions(self):
        self.client.list_user_permissions("guest")

    @recorder.use_cassette
    def test_whoami(self):
        self.client.whoami()

    @recorder.use_cassette
    def test_list_permissions(self):
        self.client.list_permissions()

    @recorder.use_cassette
    def test_get_user_permissions(self):
        self.client.get_user_permissions("guest")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_set_user_permissions(self):
        self.client.set_user_permissions("alice", configure=".*", write=".*", read=".*")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_delete_user_permissions(self):
        self.client.delete_user_permissions("alice")

    @recorder.use_cassette
    def test_list_parameters(self):
        self.client.list_parameters()

    @recorder.use_cassette
    def test_list_component_parameters(self):
        self.client.list_component_parameters("shovel")

    @recorder.use_cassette
    def test_list_vhost_component_parameters(self):
        self.client.list_vhost_component_parameters("shovel")

    @recorder.use_cassette
    def test_get_parameter(self):
        self.client.get_parameter("my-shovel-parm", "shovel")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_set_parameter(self):
        shovel_parameter = {
            'component': 'shovel',
            'value': {
                'src-exchange-key': '#',
                'src-uri': 'amqp://localhost:15672',
                'src-exchange': 'test-exchange',
                'dest-uri': 'amqp://localhost:15672',
                'dest-queue': 'test-queue',
                'ack-mode': 'on-confirm',
                'add-forward-headers': False,
                'delete-after': 'never',
            },
            'name': 'my-shovel-parm',
            'vhost': '/',
        }
        self.client.set_parameter("my-shovel-parm", "shovel", shovel_parameter)

    @recorder.use_cassette(decode_compressed_response=False)
    def test_delete_parameter(self):
        self.client.delete_parameter("my-shovel-parm", "shovel")

    @recorder.use_cassette
    def test_list_policies(self):
        self.client.list_policies()

    @recorder.use_cassette
    def test_list_vhost_policies(self):
        self.client.list_vhost_policies()

    @recorder.use_cassette
    def test_get_policy(self):
        self.client.get_policy("test-policy")

    @recorder.use_cassette(decode_compressed_response=False)
    def test_set_policy(self):
        self.client.set_policy("test-policy", "^amq", {"max-length-bytes": 1000})

    @recorder.use_cassette(decode_compressed_response=False)
    def test_delete_policy(self):
        self.client.delete_policy("test-policy")

    @recorder.use_cassette
    def test_do_aliveness_test(self):
        self.client.do_aliveness_test()

    @recorder.use_cassette
    def test_check_node_health(self):
        self.client.check_node_health()

    @recorder.use_cassette
    def test_check_node_health_with_node(self):
        self.client.check_node_health(node="rabbit@katorz")
