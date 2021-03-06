# -*- coding: utf-8 -*-

# TODO: Use Python3 to remove this fix!
from __future__ import absolute_import
import errno
import ldap
import ldap.modlist as modlist

from moulinette.core import MoulinetteError
from moulinette.authenticators import BaseAuthenticator

# LDAP Class Implementation --------------------------------------------

class Authenticator(BaseAuthenticator):
    """LDAP Authenticator

    Initialize a LDAP connexion for the given arguments. It attempts to
    authenticate a user if 'user_rdn' is given - by associating user_rdn
    and base_dn - and provides extra methods to manage opened connexion.

    Keyword arguments:
        - uri -- The LDAP server URI
        - base_dn -- The base dn
        - user_rdn -- The user rdn to authenticate

    """
    def __init__(self, name, uri, base_dn, user_rdn=None):
        super(Authenticator, self).__init__(name)

        self.uri = uri
        self.basedn = base_dn
        if user_rdn:
            self.userdn = '%s,%s' % (user_rdn, base_dn)
            self.con = None
        else:
            # Initialize anonymous usage
            self.userdn = ''
            self.authenticate(None)


    ## Implement virtual properties

    vendor = 'ldap'

    @property
    def is_authenticated(self):
        try:
            # Retrieve identity
            who = self.con.whoami_s()
        except:
            return False
        else:
            if who[3:] == self.userdn:
                return True
        return False


    ## Implement virtual methods

    def authenticate(self, password):
        try:
            con = ldap.initialize(self.uri)
            if self.userdn:
                con.simple_bind_s(self.userdn, password)
            else:
                con.simple_bind_s()
        except ldap.INVALID_CREDENTIALS:
            raise MoulinetteError(errno.EACCES, m18n.g('invalid_password'))
        except ldap.SERVER_DOWN:
            raise MoulinetteError(169, m18n.g('ldap_server_down'))
        else:
            self.con = con


    ## Additional LDAP methods
    # TODO: Review these methods

    def search(self, base=None, filter='(objectClass=*)', attrs=['dn']):
        """Search in LDAP base

        Perform an LDAP search operation with given arguments and return
        results as a list.

        Keyword arguments:
            - base -- The dn to search into
            - filter -- A string representation of the filter to apply
            - attrs -- A list of attributes to fetch

        Returns:
            A list of all results

        """
        if not base:
            base = self.basedn

        try:
            result = self.con.search_s(base, ldap.SCOPE_SUBTREE, filter, attrs)
        except:
            raise MoulinetteError(169, m18n.g('ldap_operation_error'))

        result_list = []
        if not attrs or 'dn' not in attrs:
            result_list = [entry for dn, entry in result]
        else:
            for dn, entry in result:
                entry['dn'] = [dn]
                result_list.append(entry)
        return result_list

    def add(self, rdn, attr_dict):
        """
        Add LDAP entry

        Keyword arguments:
            rdn         -- DN without domain
            attr_dict   -- Dictionnary of attributes/values to add

        Returns:
            Boolean | MoulinetteError

        """
        dn = rdn + ',' + self.basedn
        ldif = modlist.addModlist(attr_dict)

        try:
            self.con.add_s(dn, ldif)
        except:
            raise MoulinetteError(169, m18n.g('ldap_operation_error'))
        else:
            return True

    def remove(self, rdn):
        """
        Remove LDAP entry

        Keyword arguments:
            rdn         -- DN without domain

        Returns:
            Boolean | MoulinetteError

        """
        dn = rdn + ',' + self.basedn
        try:
            self.con.delete_s(dn)
        except:
            raise MoulinetteError(169, m18n.g('ldap_operation_error'))
        else:
            return True

    def update(self, rdn, attr_dict, new_rdn=False):
        """
        Modify LDAP entry

        Keyword arguments:
            rdn         -- DN without domain
            attr_dict   -- Dictionnary of attributes/values to add
            new_rdn     -- New RDN for modification

        Returns:
            Boolean | MoulinetteError

        """
        dn = rdn + ',' + self.basedn
        actual_entry = self.search(base=dn, attrs=None)
        ldif = modlist.modifyModlist(actual_entry[0], attr_dict, ignore_oldexistent=1)

        try:
            if new_rdn:
                self.con.rename_s(dn, new_rdn)
                dn = new_rdn + ',' + self.basedn

            self.con.modify_ext_s(dn, ldif)
        except:
            raise MoulinetteError(169, m18n.g('ldap_operation_error'))
        else:
            return True

    def validate_uniqueness(self, value_dict):
        """
        Check uniqueness of values

        Keyword arguments:
            value_dict -- Dictionnary of attributes/values to check

        Returns:
            Boolean | MoulinetteError

        """
        for attr, value in value_dict.items():
            if not self.search(filter=attr + '=' + value):
                continue
            else:
                raise MoulinetteError(errno.EEXIST,
                                      m18n.g('ldap_attribute_already_exists',
                                             attr, value))
        return True
