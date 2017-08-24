#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PURPOSE: Tools to access the Meetup.com API
AUTHOR: dylangregersen
DATE: Mon Sep 15 00:12:21 2014
"""
# ########################################################################### #

from __future__ import print_function, division, unicode_literals

import os
import requests
from datetime import datetime
from datetime import timedelta
from time import sleep
from urllib import urlencode


class MeetupClient(object):
    """ MeetupClient """

    rate_limit_remaining = 100
    rate_limit_reset = 1
    last_response_time = None

    def __init__(self, api_key):
        """ Find your api_key from https://secure.meetup.com/meetup_api/key/"""
        self.api_key = api_key
        self._cached_request_urls = {}

    def signed_request_url(self, meetup_method, params=None, request_hash=None):
        """To GET data from api.meetup.com"""
        if request_hash is not None and request_hash in self._cached_request_urls:
            return self._cached_request_urls[request_hash]

        # get the parameters
        params = params.copy() if params is not None else {}
        params['signed'] = True

        response = self.invoke(meetup_method, params, method='GET')
        signed_url = response['signed_url']
        if request_hash is not None:
            self._cached_request_urls[request_hash] = signed_url
        return signed_url

    def invoke(self, meetup_method, params=None, method='GET'):
        """ For invoking a request

        Parameters
        meetup_method : string
            see http://www.meetup.com/meetup_api/docs/
        params : dict or None
            parameters passed to the request
        method : string
            'GET' or 'POST'

        Returns
        response : dict
        """
        # TODO: rename invoke to http_response

        # get the parameters
        params = params.copy() if params is not None else {}
        params['key'] = self.api_key
        params['page'] = 1000

        # the specific meetup method
        # see http://www.meetup.com/meetup_api/docs/
        if meetup_method.startswith("/"):
            meetup_method = meetup_method[1:]
        url = os.path.join("https://api.meetup.com", meetup_method)

        self._wait_on_rate_limit_reached()
        # get response
        if method == 'GET':
            return self._get(url, params)
        elif method == 'POST':
            return self._post(url, params)
        elif method == 'DELETE':
            return self._delete(url, params)

    def get_next_page(self, page):
        """Returns the next page for previous page result.

        Args:
            page (dict): page result from prior invoke call

        Returns:
            None if no next page, or fetched next page
        """
        if not page.has_key('meta'):
            return None
        if not page['meta'].has_key('next'):
            return None
        url = page['meta']['next']
        self._wait_on_rate_limit_reached()
        return self._get(url, {})

    def _wait_on_rate_limit_reached(self):
        """Waits for the end of the rate limit time window.
        """
        if self.rate_limit_remaining > 0:
            return
        if not self.last_response_time:
            return
        reset_delta = timedelta(seconds=self.rate_limit_reset)
        end_of_window = self.last_response_time + reset_delta
        if end_of_window < datetime.now():
            return
        wait_delta = (end_of_window - datetime.now())
        wait_seconds = (86400 * wait_delta.days) + wait_delta.seconds
        if wait_delta.microseconds:
            wait_seconds += 1
        sleep(wait_seconds)

    def _capture_rate_limit(self, response):
        """Captures Meetup response rate limit information.

        Enables future calls to avoid failed requests due to rate limiting.
        Should be called immediately after every response from the API.

        Args:
            response (HTTPResponse): response from the last request
        """
        self.last_response_time = datetime.now()
        headers = response.headers
        try:
            self.rate_limit_remaining = int(headers['X-RateLimit-Remaining'])
            self.rate_limit_reset = int(headers['X-RateLimit-Reset'])
        except KeyError:
            pass

    def _delete(self, url, kwargs):
        response = requests.delete(url, params=kwargs).text
        try:
            self._capture_rate_limit(response)
            return response.json()
        except:
            return None

    def _get(self, url, kwargs):
        url = "{}?{}".format(url, urlencode(kwargs))
        response = requests.get(url)
        try:
            self._capture_rate_limit(response)
            return response.json()
        except:
            return None

    def _post(self, url, kwargs):
        response = requests.post(url, data=kwargs).text
        try:
            self._capture_rate_limit(response)
            return response.json()
        except:
            return None

    def get_events(self, id_type="group", **kwargs):
        kwargs = kwargs.copy()
        kwargs.setdefault('status', "upcoming,past")
        return self.invoke("2/events", kwargs)

    def create_event(self, **kwargs):
        return self.invoke('2/event/', kwargs, method='POST')

    def delete_event(self, event_id):
        return self.invoke('2/event/{}'.format(event_id), method='DELETE')

    def update_event(self, event_id, **kwargs):
        return self.invoke(
            '2/event/{}'.format(event_id),
            kwargs,
            method='POST'
        )

    def create_venue(self, group_urlname, **kwargs):
        return self.invoke(
            group_urlname + "/venues",
            kwargs,
            method="POST"
        )

    def get_profiles(self, **kwargs):
        return self.invoke('2/profiles/', kwargs)
