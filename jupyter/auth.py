# -*- coding: utf-8 -*-
from jupyterhub.auth import Authenticator


class TextinatorAuthenticator(Authenticator):
    def authenticate(self, handler, data):
        return ""
