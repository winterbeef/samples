#!/usr/bin/env python
"""
Copyright 2013 Psyop Inc.
Author: Wellington Fan <wfan@psyop.tv>
"""
import constants as C
import activedirectory

class Filter(object):
    """
    LDAP query objects, which emit() LDAP-conformant queries.
    """
    def Or(self, *filters):
        """
        Combines the query with given queries using boolean OR.
        """
        return Or(self, *filters)

    def And(self, *filters):
        """
        Combines the query with given queries using boolean AND.
        """
        return And(self, *filters)

    def Not(self):
        """
        Negates the query.
        """
        return Not(self)


class IsDisabled(Filter):
    """
    Account is disabled.
    """
    def emit(self):
        """
        Produce LDAP-conformant query.
        """
        return '(userAccountControl:%s:=%s)' % (C._AND, C.ACCOUNTDISABLE)


class IsActive(Filter):
    """
    Account is enabled.
    """
    def emit(self):
        """
        Produce LDAP-conformant query.
        """
        return Not(IsDisabled()).emit()


class Check(Filter):
    """
    Simple property comparison.
    """
    def __init__(self, name, value, op='='):
        """
        Take a property name, a comparison operator, and a value. E.g:
        'cn', 'jonh*', '='
        """
        self.name = name
        self.value = value
        self.op = op

    def emit(self):
        """
        Produce LDAP-conformant query.
        """
        return "(%s%s%s)" % (self.name, self.op, self.value)


class DescendantOf(Filter):
    """
    Find descendants.
    """
    def __init__(self, parent):
        self.parent = parent

    def emit(self):
        """
        Produce LDAP-conformant query.
        """
        val = (C._CHAIN, self.parent)
        return '(memberOf:%s:=CN=%s,cn=Users,dc=psyop,dc=tv)' % val


class ChildOf(Filter):
    """
    Find immediate children.
    """
    def __init__(self, parent):
        self.parent = parent

    def emit(self):
        """
        Produce LDAP-conformant query.
        """
        return '(memberOf=CN=%s,CN=Users,DC=psyop,DC=tv)' % (self.parent,)


class Composite(Filter):
    """
    A Filter composed of other Filters.
    """
    def __init__(self, *filters):
        self.filters = filters

    def concat(self, op):
        """
        Provides the generic composition rules for multiple filters.
        """
        filter_train = ''.join([f.emit() for f in self.filters])
        return '(%s%s)' % (op, filter_train)


class And(Composite):
    """
    Boolean AND the list of components.
    """
    def emit(self):
        """
        Produce LDAP-conformant query.
        """
        return self.concat('&')


class Or(Composite):
    """
    Boolean OR the list of components.
    """
    def emit(self):
        """
        Produce LDAP-conformant query.
        """
        return self.concat('|')


class Not(Composite):
    """
    Negate the given filter.
    """
    def __init__(self, filter):
        """
        This Composite filter takes only ONE filter as an argument.
        """
        self.filters = [filter]

    def emit(self):
        """
        Produce LDAP-conformant query.
        """
        return self.concat('!')


def test_filters():
    filters = {
        "IsDisabled()": IsDisabled(),
        "IsActive()": IsActive(),
        "ChildOf('systems')": ChildOf('systems'),
        "Check('objectClass', 'Person')": Check('objectClass', 'Person'),
        "Check('objectCategory', 'Group')": Check('objectCategory', 'Group'),
        "Check('accountExpires', '1', '>=')": Check('accountExpires', '1', '>='),
        "DescendantOf('Google Groups')": DescendantOf('Google Groups'),
    }

    filters['Compound'] = IsActive().And(
        Check('objectClass', 'Person'),
        Check('accountExpires', '1', '>=')).Or(filters["DescendantOf('Google Groups')"])

    return filters

def print_filters(filters):
    for i, j in filters.iteritems():
        print "%-48s: %s" % (i, j.emit())


if __name__ == '__main__':
    ad = activedirectory.ActiveDirectory.create()
    filters = test_filters()

    print_filters(filters)

    for i, j in filters.iteritems():
        print '==FILTER: {}=========='.format(i)
        result = ad.execute(j.emit())
        print "\n".join([r['cn'][0] for (dn, r) in result])
        print

