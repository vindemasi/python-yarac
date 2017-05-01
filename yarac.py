# yarac.py - python RabbitMQ api client
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

"""
yarac - provide a client to interact with the RabbiMQ management API.

@author: Vincenzo Demasi
@license: MIT License
@contact: vindemasi@gmail.com
"""

__author__ = "Vincenzo Demasi"
__copyright__ = "Copyright 2016-2017, Vincenzo Demasi"
__license__ = "MIT"
__version__ = "0.1.0"


import json
from urllib.parse import quote_plus as quote

import requests

__all__ = [
    'DIRECT', 'TOPIC', 'HEADERS', 'FANOUT',
    'Error', 'ParameterError', 'RequestError', 'RedirectionError',
    'BadRequestError', 'ServerError', 'Client'
]

DIRECT = 'direct'
TOPIC = 'topic'
HEADERS = 'headers'
FANOUT = 'fanout'


class Error(Exception):
    """Base error exception."""


class ParameterError(Error):
    """Raised when the given parameters are invalid."""


class RequestError(Error):
    """Raised when the request give a request error"""

    def __init__(self, *, code=None, reason=None):
        self.code = code
        self.reason = reason

    def __str__(self):
        return "Error {error.code}: {error.reason}".format(error=self)


class RedirectionError(RequestError):
    """Raised when the request give a 3xx error"""


class BadRequestError(RequestError):
    """Raised when the request give a 4xx error"""


class ServerError(RequestError):
    """Raised when the request give a 5xx error"""


class Client:
    """RabbitMQ management API client"""

    def __init__(self, api_prefix, *, preferred_vhost="/", allow_redirects: bool = False):
        """Create a RabbitMQ api client.

        :param api_prefix: the url prefix of the api
            (Ex. http://guest:guest@localhost:15672/api)
        :param preferred_vhost: used whenever a virtual host is required
            and a None values is used instead. It should be unquoted (i.e.
            use "/" and not "%2F", it will be quoted internally)
        :param allow_redirects: if True allow to follow redirection during request;
            otherwise an error is raised.
        """
        self.api_root = api_prefix.rstrip("/")
        self.vhost = preferred_vhost
        self.allow_redirects = allow_redirects

    def build_url(self, template: str, **kwargs) -> str:
        """Build an api url from a template and a mapping.

        :param template: a template that looks like /exchanges/{vhost}/{name}
        :param kwargs: the dict used with the template.format function. The
            dict values are quoted internally (this means they are passed unquoted).

        :return: the complete url to request to request on
        """
        quoted = {k: quote(v) for k, v in kwargs.items()}
        suffix = template.format(**quoted).lstrip("/")
        return "{prefix}/{suffix}".format(prefix=self.api_root, suffix=suffix)

    def request(self, method: str, endpoint: str, *,
                data: dict = None, params: dict = None,
                headers: dict = None):
        """Send a request to the api.

        :param method: one of 'get', 'put', 'delete' or 'post'
        :param endpoint: the api url to ask
        :param data: request data (used only with 'put' or 'post' methods)
        :param params: request params
        :param headers: request headers (by default Content-Type: application/json
            is sent)

        :return: the given response (object if response is json otherwise str)
        :raise ParameterError: if the request method is not supported
        :raise RedirectionError: if status is 3xx and redirection is not allowed
        :raise BadRequestError: if status is 4xx
        :raise ServerError: if status is 5xx
        :raise RequestError: if status isn't in 2xx, 3xx, 4xx or 5xx (should never happens)
        """
        method = method.lower()
        req_headers = {"Content-type": "application/json"}
        if headers:
            req_headers.update(headers)

        if method in {"get", "delete"}:
            data = None
        elif method in {"put", "post"}:
            data = json.dumps(data)
        else:
            raise ParameterError("only GET, PUT, DELETE and POST "
                                 "methods are supported")

        response = requests.request(method, endpoint,
                                    data=data,
                                    params=params,
                                    headers=req_headers,
                                    allow_redirects=self.allow_redirects)

        if 200 <= response.status_code < 300:
            no_content = response.headers.get("Content-Length", '0') == '0'
            return response.json() if not no_content else None

        if 300 <= response.status_code < 400:
            raise RedirectionError(code=response.status_code, reason=response.reason)

        if 400 <= response.status_code < 500:
            raise BadRequestError(code=response.status_code, reason=response.reason)

        if 500 <= response.status_code < 600:
            raise ServerError(code=response.status_code, reason=response.reason)

        raise RequestError(code=response.status_code, reason=response.reason)

    def get_overview(self):
        """Get various random bits of information that describe the whole system.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/overview")
        return self.request('get', endpoint)

    def get_cluster_name(self):
        """Get the name identifying this RabbitMQ cluster.

        :return: something like {'name': 'rabbit@server'}

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/cluster-name")
        return self.request('get', endpoint)

    def set_cluster_name(self, name: str):
        """Set the name identifying this RabbitMQ cluster.

        :param name: the name of the cluster

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/cluster-name")
        return self.request('put', endpoint, data=dict(name=name))

    def list_cluster_nodes(self):
        """Get a list of nodes in the RabbitMQ cluster.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/nodes")
        return self.request('get', endpoint)

    def get_cluster_node(self, node: str, *, memory: bool = False, binary: bool = False):
        """Get an individual node in the RabbitMQ cluster.

        :param node: the node name
        :param binary: get memory statistics
        :param memory: get a breakdown of binary memory use (may be expensive if
            there are many small binaries in the system)

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/nodes/{node}", node=node)
        opts = dict(memory=memory, binary=binary).items()
        return self.request('get', endpoint, params={k: "true" for k, v in opts if v})

    def list_management_extensions(self):
        """Get a list of extensions of the management plugin.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/extensions")
        return self.request('get', endpoint)

    def export_server_definitions(self):
        """Get the server definitions.

         Exchanges, queues, bindings, users, virtual hosts, permissions and parameters.
         Everything apart from messages.

        See :func:`~yarac.Client.request` for raised Errors
         """
        endpoint = self.build_url("/definitions")
        return self.request('get', endpoint)

    def merge_server_definitions(self, definitions):
        """Merge the server definitions.

          :param definitions: the definitions to load (a json compatible object)

        - The definitions are merged. Anything already existing on the server
          but not in the uploaded definitions is untouched.
        - Conflicting definitions on immutable objects (exchanges, queues
          and bindings) will cause an error.
        - Conflicting definitions on mutable objects will cause the object in
          the server to be overwritten with the object from the definitions.
        - In the event of an error you will be left with a part-applied set
          of definitions.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/definitions")
        return self.request('post', endpoint, data=definitions)

    def export_vhost_definitions(self, *, vhost: str = None):
        """Get the server definitions for a given virtual host.

        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        Exchanges, queues, bindings, users, virtual hosts, permissions and parameters.
        Everything apart from messages.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/definitions/{vhost}", vhost=vhost)
        return self.request('get', endpoint)

    def merge_vhost_definitions(self, definitions, *, vhost: str = None):
        """Merge the server definitions for a given virtual host.

         :param definitions: the definitions to load (a json compatible object)
         :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        - The definitions are merged. Anything already existing on the server
          but not in the uploaded definitions is untouched.
        - Conflicting definitions on immutable objects (exchanges, queues
          and bindings) will cause an error.
        - Conflicting definitions on mutable objects will cause the object in
          the server to be overwritten with the object from the definitions.
        - In the event of an error you will be left with a part-applied set
          of definitions.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/definitions/{vhost}", vhost=vhost)
        return self.request('post', endpoint, data=definitions)

    def list_connections(self):
        """Get a list of all open connections.

        See :func:`~yarac.Client.request` for raised Errors
        """
        path = self.build_url("/connections")
        return self.request('get', path)

    def list_vhost_connections(self, *, vhost: str = None):
        """A list of all open connections in a specific vhost.

         :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/vhosts/{vhost}/connections", vhost=vhost)
        return self.request('get', endpoint)

    def get_connection(self, connection: str):
        """Get an individual connection.

        :param connection: the connection name

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/connections/{connection}", connection=connection)
        return self.request('get', endpoint)

    def drop_connection(self, connection: str, *, reason: str = None):
        """Drop an individual connection.

        :param connection: the name of the connection to drop
        :param reason: the reason of connection deletion

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/connections/{connection}", connection=connection)
        headers = {"X-Reason": reason} if reason else None
        return self.request('delete', endpoint, headers=headers)

    def list_connection_channels(self, connection: str):
        """Get the list of all channels for a given connection.

        :param connection: the connection name

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/connections/{connection}/channels", connection=connection)
        return self.request('get', endpoint)

    def list_channels(self):
        """Get a list of all open channels.

        See :func:`~yarac.Client.request` for raised Errors
        """
        path = self.build_url("/channels")
        return self.request('get', path)

    def list_vhost_channels(self, *, vhost: str = None):
        """Get a list of all open channels in a specific vhost.

         :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/vhosts/{vhost}/channels", vhost=vhost)
        return self.request('get', endpoint)

    def get_channel(self, channel: str):
        """Get details about an individual channel.

        :param channel: the channel name

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/channels/{channel}", channel=channel)
        return self.request('get', endpoint)

    def list_consumers(self):
        """Get a list of all consumers.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/consumers")
        return self.request('get', endpoint)

    def list_vhost_consumers(self, *, vhost: str = None):
        """Get a list of all consumers in a given virtual host.

        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/consumers/{vhost}", vhost=vhost)
        return self.request('get', endpoint)

    def list_exchanges(self):
        """Get a list of all exchanges.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/exchanges")
        return self.request('get', endpoint)

    def list_vhost_exchanges(self, *, vhost: str = None):
        """Get a list of all exchanges in a given virtual host.

        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/exchanges/{vhost}", vhost=vhost)
        return self.request('get', endpoint)

    def get_exchange(self, exchange: str, *, vhost: str = None):
        """Get an individual exchange in the given virtual host.

        :param exchange: the exchange name (known issue the default exchange
            could be retrieved only by listing all and the filtering the list)
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/exchanges/{vhost}/{exchange}", vhost=vhost, exchange=exchange)
        if exchange == "":
            # workaround: as the exchange is "" then it couldn't be get directly
            for result in self.request('get', endpoint):
                # noinspection PyTypeChecker
                if result['name'] == '':
                    return result
        else:
            return self.request('get', endpoint)

    # noinspection PyShadowingBuiltins
    def declare_exchange(self, exchange: str, type: str = "direct", *,
                         durable: bool = True, auto_delete: bool = False,
                         internal: bool = False, arguments: dict = None,
                         vhost: str = None):
        """Declare an exchanges in a given virtual host.

        :param exchange: the name of the exchange
        :param type: the type of the exchange
        :param auto_delete: the auto-delete status
        :param durable: the durability status
        :param internal: the internal status
        :param arguments: the arguments
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/exchanges/{vhost}/{exchange}", vhost=vhost, exchange=exchange)
        data = dict(type=type, auto_delete=auto_delete, durable=durable,
                    internal=internal, arguments=arguments or {})
        return self.request('put', endpoint, data=data)

    def delete_exchange(self, exchange: str, *, unused_only: bool = False, vhost: str = None):
        """Delete an exchange in a given virtual host.

        :param exchange: the name of the exchange
        :param unused_only: if true prevent the deletion if the exchange is bound to
            a queue or it's the source of another exchange. If that case an exception is raised.
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/exchanges/{vhost}/{exchange}", vhost=vhost, exchange=exchange)
        params = {"if-unused": "true"} if unused_only else None
        return self.request('delete', endpoint, params=params)

    def list_exchange_outgoing_bindings(self, exchange: str, *, vhost: str = None):
        """Get a list of all bindings in the given virtual host in which a
        given exchange is the source.

        :param exchange: the exchange name which is the source of the bindings
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/exchanges/{vhost}/{exchange}/bindings/source", vhost=vhost, exchange=exchange)
        return self.request('get', endpoint)

    def list_exchange_incoming_bindings(self, exchange: str, *, vhost: str = None):
        """Get a list of all bindings in the given virtual host in which a
        given exchange is the destination.

        :param exchange: the exchange name which is the source of the bindings
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/exchanges/{vhost}/{exchange}/bindings/destination", vhost=vhost, exchange=exchange)
        return self.request('get', endpoint)

    def publish_message(self, exchange: str, *, routing_key: str = "", payload: str = "",
                        payload_encoding: str = "string",
                        properties: dict = None, vhost: str = None):
        """Publish a message to an exchange
        :param exchange: the name of the target exchange
        :param routing_key: the routing key
        :param payload; the payload of the message
        :param payload_encoding: if "string" the payload is treated as UTF-8, if "base64"
            the payload is treated as base64 encoded.
        :param properties: the properties of the message - see RabbitMQ docs for details
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        If the message is published successfully, the response will look like:

        {"routed": true}

        routed will be true if the message was sent to at least one queue.

        Please note that the HTTP API is not ideal for high performance publishing;
        the need to create a new TCP connection for each message published can
        limit message throughput compared to AMQP or other protocols using
        long-lived connections.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/exchanges/{vhost}/{exchange}/publish", vhost=vhost, exchange=exchange)
        data = dict(
            routing_key=routing_key,
            payload=payload,
            payload_encoding=payload_encoding,
            properties=properties or {},
        )
        return self.request('post', endpoint, data=data)

    def list_queues(self):
        """Get a list of all queues.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/queues")
        return self.request('get', endpoint)

    def list_vhost_queues(self, *, vhost: str = None):
        """Get a list of all queues in a given virtual host.

        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/queues/{vhost}", vhost=vhost)
        return self.request('get', endpoint)

    def get_queue(self, queue: str, *, vhost: str = None):
        """Get an individual queue in the given virtual host.

        :param queue: the queue name
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/queues/{vhost}/{queue}", vhost=vhost, queue=queue)
        return self.request('get', endpoint)

    def declare_queue(self, queue: str, *, durable: bool = True, auto_delete: bool = False,
                      arguments: dict = None, node: str = None, vhost: str = None):
        """Declare a queue in the given virtual host.

        :param queue: the queue name
        :param durable: queue durability
        :param auto_delete: if True, the queue will delete itself after at
            least one consumer has connected, and then all consumers
            have disconnected.
        :param arguments: queue arguments
        :param node: the queue node
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/queues/{vhost}/{queue}", vhost=vhost, queue=queue)
        data = dict(
            auto_delete=auto_delete,
            durable=durable,
        )
        if arguments is not None:
            data["arguments"] = arguments
        if node is not None:
            data["node"] = node
        return self.request('put', endpoint, data=data)

    def delete_queue(self, queue: str, *, empty_only: bool = False, unused_only: bool = False, vhost: str = None):
        """Delete a queue in the given vhost.

        :param queue: the queue name
        :param empty_only: prevent the deletion if the queue contains messages
        :param unused_only: prevent the deletion if the queue has consumers
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/queues/{vhost}/{queue}", vhost=vhost, queue=queue)
        params = {k: 'true' for k, v in {
            "if-empty": empty_only,
            "if-unused": unused_only}.items() if v}
        return self.request('delete', endpoint, params=params)

    def list_queue_bindings(self, queue: str, *, vhost: str = None):
        """List the bindings of a queue in the given vhost.

        :param queue: the queue name
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/queues/{vhost}/{queue}/bindings", vhost=vhost, queue=queue)
        return self.request('get', endpoint)

    def purge_queue(self, queue: str, *, vhost: str = None):
        """Purge a queue in the given vhost.

        :param queue: the queue name
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/queues/{vhost}/{queue}/contents", vhost=vhost, queue=queue)
        return self.request('delete', endpoint)

    def do_queue_action(self, queue: str, action: str, *, vhost: str = None):
        """Do an action on a queue.

        :param queue: the queue name
        :param action: the action to perform. Currently the actions which are
            supported are "sync" and "cancel_sync"
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/queues/{vhost}/{queue}/actions", vhost=vhost, queue=queue)
        return self.request('post', endpoint, data=dict(action=action))

    def get_messages(self, queue: str, *, count: int = 1, requeue: bool = True, encoding: str = "auto",
                     truncate: int = None, vhost: str = None):
        """Get messages from a queue.

        :param queue: the queue name
        :param count: the maximum number of messages to get. You may get fewer
            messages than this if the queue cannot immediately provide them.
        :param requeue: determines whether the messages will be removed from
            the queue. If requeue is true they will be requeued - but their
            redelivered flag will be set.
        :param encoding: must be either "auto" (in which case the payload will
            be returned as a string if it is valid UTF-8, and base64 encoded
            otherwise), or "base64" (in which case the payload will always be
            base64 encoded).
        :param truncate: if not None, it will truncate the message payload
            if it is larger than the size given (in bytes).
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/queues/{vhost}/{queue}/get", vhost=vhost, queue=queue)
        data = dict(count=count, requeue=requeue, encoding=encoding)
        if truncate is not None:
            data["truncate"] = truncate
        return self.request('post', endpoint, data=data)

    def list_bindings(self):
        """Get a list of all bindings.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/bindings")
        return self.request('get', endpoint)

    def list_vhost_bindings(self, *, vhost: str = None):
        """Get A list of all bindings in a given virtual host.

        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/bindings/{vhost}", vhost=vhost)
        return self.request('get', endpoint)

    def list_exchange_to_queue_bindings(self, exchange: str, queue: str, *, vhost: str = None):
        """A list of all bindings between an exchange and a queue.

        :param exchange: the source exchange name
        :param queue: the destination queue name
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/bindings/{vhost}/e/{exchange}/q/{queue}", vhost=vhost, exchange=exchange,
                                  queue=queue)
        return self.request('get', endpoint)

    def get_exchange_to_queue_binding(self, exchange: str, queue: str, props: str, *, vhost: str = None):
        """Get a binding between an exchange and a queue.

        :param exchange: the source exchange name
        :param queue: the destination queue name
        :param props: is a "name" for the binding composed of its routing key and a hash of its arguments.
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/bindings/{vhost}/e/{exchange}/q/{queue}/{props}",
                                  vhost=vhost, exchange=exchange, queue=queue, props=props)
        return self.request('get', endpoint)

    def declare_exchange_to_queue_binding(self, exchange: str, queue: str, *, routing_key: str = "",
                                          arguments: dict = None,
                                          vhost: str = None):
        """Create a binding between an exchange and a queue.

        :param exchange: the source exchange name
        :param queue: the destination queue name
        :param routing_key: the routing key of thr binding (optional)
        :param arguments: the arguments dict (optional)
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/bindings/{vhost}/e/{exchange}/q/{queue}", vhost=vhost, exchange=exchange,
                                  queue=queue)
        data = dict(routing_key=routing_key, arguments=arguments or {})
        return self.request('post', endpoint, data=data)

    def delete_exchange_to_queue_binding(self, exchange: str, queue: str, props: str, *, vhost: str = None):
        """Delete a binding between an exchange and a queue.

        :param exchange: the source exchange name
        :param queue: the destination queue name
        :param props: is a "name" for the binding composed of its routing key and a hash of its arguments.
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/bindings/{vhost}/e/{exchange}/q/{queue}/{props}",
                                  vhost=vhost, exchange=exchange, queue=queue, props=props)
        return self.request('delete', endpoint)

    def list_exchange_to_exchange_bindings(self, source: str, destination: str, *, vhost: str = None):
        """Get a list of all bindings between two exchanges.

        :param source: the source exchange name
        :param destination: the destination exchange name
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/bindings/{vhost}/e/{source}/e/{destination}",
                                  vhost=vhost, source=source, destination=destination)
        return self.request('get', endpoint)

    def get_exchange_to_exchange_binding(self, source: str, destination: str, props: str, *, vhost: str = None):
        """Get a binding between two exchanges.

        :param source: the source exchange name
        :param destination: the destination exchange name
        :param props: is a "name" for the binding composed of its routing key and a hash of its arguments.
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/bindings/{vhost}/e/{source}/e/{destination}/{props}",
                                  vhost=vhost, source=source, destination=destination, props=props)
        return self.request('get', endpoint)

    def declare_exchange_to_exchange_binding(self, source: str, destination: str, *, routing_key: str = "",
                                             arguments: dict = None,
                                             vhost: str = None):
        """Create a binding between an exchange and a queue.

        :param source: the source exchange name
        :param destination: the destination exchange name
        :param routing_key: the routing key of thr binding (optional)
        :param arguments: the arguments dict (optional)
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/bindings/{vhost}/e/{source}/e/{destination}",
                                  vhost=vhost, source=source, destination=destination)
        data = dict(routing_key=routing_key, arguments=arguments or {})
        return self.request('post', endpoint, data=data)

    def delete_exchange_to_exchange_binding(self, source: str, destination: str, props: str, *,
                                            vhost: str = None):
        """Delete a binding between two exchanges.

        :param source: the source exchange name
        :param destination: the destination exchange name
        :param props: is a "name" for the binding composed of its routing key and a hash of its arguments.
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/bindings/{vhost}/e/{source}/e/{destination}/{props}",
                                  vhost=vhost, source=source, destination=destination, props=props)
        return self.request('delete', endpoint)

    def list_virtual_hosts(self):
        """Get a list of all virtual hosts.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/vhosts")
        return self.request('get', endpoint)

    def get_virtual_host(self, *, vhost: str = None):
        """Get an individual virtual host.

        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/vhosts/{vhost}", vhost=vhost)
        return self.request('get', endpoint)

    def declare_virtual_host(self, vhost: str, *, tracing: bool = None):
        """declare a virtual host.

        :param vhost: the vhost name
        :param tracing: enable/disable tracing (if None tracing isn't changed)

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/vhosts/{vhost}", vhost=vhost)
        data = dict(tracing=tracing) if tracing is not None else {}
        return self.request('put', endpoint, data=data)

    def delete_virtual_host(self, vhost: str):
        """Delete a virtual host.

        :param vhost: the vhost name.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/vhosts/{vhost}", vhost=vhost)
        return self.request('delete', endpoint)

    def list_vhost_permissions(self, *, vhost=None):
        """A list of all permissions for a given virtual host.

        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/vhosts/{vhost}/permissions", vhost=vhost)
        return self.request('get', endpoint)

    def list_users(self):
        """Get a list of all users.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/users")
        return self.request('get', endpoint)

    def get_user(self, username: str):
        """Get a user by username.

        :param username: the username

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/users/{username}", username=username)
        return self.request('get', endpoint)

    def set_user(self, username, *, password: str = None, password_hash: str = None, tags: str = ""):
        """Create or update a user.

        :param username: the name that identify the user
        :param password: the user password
        :param password_hash: the user hashed password
        :param tags: is a comma-separated list of tags.

        Currently recognised tags (from the management plugin) are "administrator",
        "monitoring", "policymaker" and "management".

        The tags key is mandatory, albeit it could be "".
        Either password or password_hash must be set.
        Setting password_hash to "" will ensure the
        user cannot use a password to log in.

        See :func:`~yarac.Client.request` for raised Errors
        """
        data = dict(tags=tags)
        if password is not None:
            data["password"] = password
        elif password_hash is not None:
            data["password_hash"] = password_hash
        endpoint = self.build_url("/users/{username}", username=username)
        return self.request('put', endpoint, data=data)

    def delete_user(self, username: str):
        """Delete a user.e name

        :param username: the name that identify the user

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/users/{username}", username=username)
        return self.request('delete', endpoint)

    def list_user_permissions(self, username: str):
        """Get the list of all permissions for a given user.

        :param username: the name that identify the user

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/users/{username}/permissions", username=username)
        return self.request('get', endpoint)

    def whoami(self):
        """Get details of the currently authenticated user.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/whoami")
        return self.request('get', endpoint)

    def list_permissions(self):
        """Get a list of all permissions for all users.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/permissions")
        return self.request('get', endpoint)

    def get_user_permissions(self, username: str, *, vhost: str = None):
        """Get the permissions of a user on a virtual host

        :param username: the name that identify the user
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/permissions/{vhost}/{username}", vhost=vhost, username=username)
        return self.request('get', endpoint)

    def set_user_permissions(self, username: str, configure: str, write: str, read: str, *, vhost: str = None):
        """Set the permissions of a user on a virtual host.

        :param username: the name that identify the user
        :param configure: configure permissions as a regular expression ('' is a shortcut for '^$')
        :param write: write permissions as a regular expression ('' is a shortcut for '^$')
        :param read: read permissions as a regular expression ('' is a shortcut for '^$')
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        All permissions are required, however if they are None but they was
        already saved then saved values are used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/permissions/{vhost}/{username}", vhost=vhost, username=username)
        data = dict(configure=configure, write=write, read=read)
        return self.request('put', endpoint, data=data)

    def delete_user_permissions(self, username: str, *, vhost: str = None):
        """Delete permissions of a user on a virtual host

        :param username: the name that identify the user
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/permissions/{vhost}/{username}", vhost=vhost, username=username)
        return self.request('delete', endpoint)

    def list_parameters(self):
        """Get a list of all parameters.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/parameters")
        return self.request('get', endpoint)

    def list_component_parameters(self, component: str):
        """Get a list of all parameters for a given component.

        :param component: the name of the component

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/parameters/{component}", component=component)
        return self.request('get', endpoint)

    def list_vhost_component_parameters(self, component: str, *, vhost: str = None):
        """Get a list of all parameters for a given component and virtual host.

        :param component: the name of the component
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/parameters/{component}/{vhost}", component=component, vhost=vhost)
        return self.request('get', endpoint)

    def get_parameter(self, parameter: str, component: str, *, vhost: str = None):
        """Get an a parameter for a given component and virtual host.

        :param parameter: the parameter name
        :param component: the name of the component
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/parameters/{component}/{vhost}/{parameter}", component=component, vhost=vhost,
                                  parameter=parameter)
        return self.request('get', endpoint)

    def set_parameter(self, parameter: str, component: str, value: dict, *, vhost: str = None):
        """Set a parameter for a given component and virtual host.

        :param parameter: the parameter name
        :param component: the name of the component
        :param vhost: the vhost name, if it is None the client default vhost
        :param value: the parameter value
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/parameters/{component}/{vhost}/{parameter}",
                                  component=component, vhost=vhost, parameter=parameter)
        return self.request('put', endpoint, data=value)

    def delete_parameter(self, parameter: str, component: str, *, vhost: str = None):
        """Delete a parameter for a given component and virtual host.

        :param parameter: the parameter name
        :param component: the name of the component
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/parameters/{component}/{vhost}/{parameter}", component=component, vhost=vhost,
                                  parameter=parameter)
        return self.request('delete', endpoint)

    def list_policies(self):
        """Get a list of all policies.

        See :func:`~yarac.Client.request` for raised Errors
        """
        endpoint = self.build_url("/policies")
        return self.request('get', endpoint)

    def list_vhost_policies(self, *, vhost: str = None):
        """A list of all policies in a given virtual host.

        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/policies/{vhost}", vhost=vhost)
        return self.request('get', endpoint)

    def get_policy(self, policy: str, *, vhost: str = None):
        """Get an individual policy in a given virtual host.

        :param policy: the policy name
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/policies/{vhost}/{policy}", vhost=vhost, policy=policy)
        return self.request('get', endpoint)

    def set_policy(self, policy: str, pattern: str, definition: dict, *, priority: int = 0,
                   apply_to: str = "all", vhost: str = None):
        """Get an individual policy in a given virtual host.

        :param policy: the policy name
        :param pattern: a regular expression for policy match
        :param definition: a dict containing the definitions
        :param priority: the policy priority
        :param apply_to: target of the policy ("exchanges", "queues" or "all")
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/policies/{vhost}/{policy}", vhost=vhost, policy=policy)
        data = dict(pattern=pattern, definition=definition, priority=priority, apply_to=apply_to)
        return self.request('put', endpoint, data=data)

    def delete_policy(self, policy: str, *, vhost: str = None):
        """Get an individual policy in a given virtual host.

        :param policy: the policy name
        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/policies/{vhost}/{policy}", vhost=vhost, policy=policy)
        return self.request('delete', endpoint)

    def do_aliveness_test(self, *, vhost: str = None):
        """Declares a test queue, then publishes and consumes a message.

        Intended for use by monitoring tools. If everything is working correctly,
        will return {"status":"ok"}.

        :param vhost: the vhost name, if it is None the client default vhost
            will be used.

        See :func:`~yarac.Client.request` for raised Errors
        """
        vhost = vhost if vhost is not None else self.vhost
        endpoint = self.build_url("/aliveness-test/{vhost}", vhost=vhost)
        return self.request('get', endpoint)

    def check_node_health(self, *, node=None):
        """Runs basic health checks on the given node.

        :param node: the name of the node to check. If None then the current
            is checked

        Checks that the rabbit application is running, channels and queues
        can be listed successfully, and that no alarms are in effect.
        If everything is working correctly, it will return {"status":"ok"}
        If something fails, it will return {"status":"failed","reason":"string"}

        See :func:`~yarac.Client.request` for raised Errors
        """
        if node is None:
            endpoint = self.build_url("/healthchecks/node")
        else:
            endpoint = self.build_url("/healthchecks/node/{node}", node=node)
        return self.request('get', endpoint)
