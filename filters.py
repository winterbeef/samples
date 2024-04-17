"""
Filters that may be composed from arbitratrily complex Boolean expressions.

This module provides generic filtering classes, suitable for refinement and
composition.  Filters may be composites -- composed of other Filters, which may
themselves composed of other Filters.

Filters have 2 important methods: test(), and filter():
 - test() takes a record and returns a boolean
 - filter() applies the test to a list, returning a list of matching elements.

These methods must be defined by all Filters subclasses.

A Composite Filters is created by passing a number of other Filters to the
constructor. E.g.:

isLiquid = And(isWater, Not(belowFreezing)).test(h2o)
 -- or --
isLiquid = isWater.And(Not(belowFreezing)).test(h2o)

There are some convenience methods that mimic Filter classes.  This allows for
an alternative syntax for chaining Filters.

1) Traditional, tree-like:
list = And(Not(isFreelance), Or(InOffice('LA'), InOffice('SYD'))).filter(people)

2) Chaining:
list = InOffice('LA').Or(InOffice('SYD')).And(Not(isFreelance)).filter(people)

Copyright 2013 Psyop Inc.
Author: Wellington Fan <wfan@psyop.tv>
"""
import re
import operator

class Filter(object):
    """
    Provides structure for filtering operations.
    """
    def __init__(self, testValue):
        """
        Saves a value against which to test.
        """
        self.testValue = testValue

    def test(self, candidate):
        """
        Abstract method. Returns a boolean -- the result of testing a candidate.
        Implementation left to concrete subclasses.
        """
        raise NotImplementedError, "Implement this method in a derived class."

    def filter(self, candidates):
        """
        Returns elements of a list which pass the test.
        """
        return filter(self.test, candidates)

    def Or(self, *moreFilters):
        """
        Presents a Filter instance as a method.
        """
        return Or(self, *moreFilters)

    def And(self, *moreFilters):
        """
        Presents a Filter instance as a method.
        """
        return And(self, *moreFilters)

    def Not(self):
        """
        Presents a Filter instance as a method.
        """
        return Not(self)


class EchoMatch(Filter):
    """
    Return the value provided at creation.
    """
    def test(self, candidate):
        return self.testValue


class PropertyRegex(Filter):
    """
    Check a property against a regex.
    """
    def __init__(self, property, pattern):
        """Save the property name and regex for later tests"""
        self.property = property
        self.pattern  = pattern

    def test(self, candidate):
        """
        Test the value of the candidate's property against the regex.
        """
        valid = re.compile(self.pattern)
        att   = getattr(candidate, self.property)
        if att:
            return valid.search(att)
        else:
            return False


class Lambda(Filter):
    """
    Accept an arbitrary callable for testing candidates.
    """
    def test(self, candidate):
        """
        Return the value of calling the test with the candidate.
        """
        return self.testValue(candidate)


class Check(Filter):
    """
    Accept a property name, a comparison operator, and a value, against which
    candidates will be tested.
    """
    def __init__(self, property, comparator, value):
        """
        Take a property name, a comparison operator, and a value.
        """
        self.property   = property
        self.comparator = self.getComparator(comparator)
        self.value      = value

    def getComparator(self, name):
        """
        Returns a standard operator from its string representation.
        """
        return {
            'in' : lambda a,b: operator.contains(b,a),
            'has': operator.contains,
            'is' : operator.eq,
            'ge' : operator.ge,
            'gt' : operator.gt,
            'le' : operator.le,
            'lt' : operator.lt,
            'ne' : operator.ne,
        }.get(name)

    def test(self, candidate):
        """
        Calls the comparator on the value of the candidate's property.
        """
        att = getattr(candidate, self.property)
        try:
            return self.comparator(att.lower(), self.value.lower())
        except:
            pass

        try:
            return self.comparator(att, self.value)
        except:
            pass

        return False


class InOffice(Filter):
    """
    Sample filter of the most basic kind.
    """
    def test(self, candidate):
        """
        Test the office of the candidate.
        """
        return candidate.office==self.testValue


class FilterComposite(Filter):
    """
    A Composite Filter is a Filter composed of other Filters.
    """
    def __init__(self, *filters):
        """
        Save a list of Filters of which this Filter is composed.
        """
        self.filters = filters

    def test(self, candidate):
        """
        Abstract method. Returns a boolean -- the result of testing a candidate.
        Implementation left to concrete subclasses.
        """
        raise NotImplementedError, "Implement this method in a derived class."


class And(FilterComposite):
    """
    A Composite Filter.
    """
    def test(self, candidate):
        """
        Perform a Boolean AND using the component Filters.
        """
        for f in self.filters:
            if not f.test(candidate):
                return False
        return True


class Or(FilterComposite):
    """
    A Composite Filter.
    """
    def test(self, candidate):
        """
        Perform a Boolean OR using the component Filters.
        """
        for f in self.filters:
            if f.test(candidate):
                return True
        return False


class Not(FilterComposite):
    """
    Inverts the sense of a Filter.
    """
    def __init__(self, subject):
        """
        Save the provided filter as the subject of inversion.
        """
        self.subject = subject

    def test(self, candidate):
        """
        Returns the inversion of the wrapped filter.
        """
        return not self.subject.test(candidate)


class Candidate(object):
    """
    A mock class for testing Filters.
    """
    def __init__(self, name, office, groups=[], data={}):
        self.name   = name
        self.office = office
        self.groups  = groups

        # Convert a dictionary in the constructor into properties.
        for k, v in data.items():
            setattr(self, k, v)

    def show(self):
        values = (self.name, self.fave, self.office, ",".join(self.groups),)
        return '<Candidate:name=%s, fave=%s, office=%s, groups=%s>' % values


def tests():
    """
    Run some simple tests.
    """
    def show(results):
        return "%s\n" % ("\n".join([result.show() for result in results]), )

    people = [
        Candidate('Alice Agnew',  'SYD', ['producers', 'staff'],     {'fave':'Red'  }),
        Candidate('Bob Brite',    'LA',  ['leads',     'staff'],     {'fave':'Red'  }),
        Candidate('Chuck Close',  'SYD', ['producers', 'freelance'], {'fave':'Red'  }),
        Candidate('Doug Dirtbag', 'NY',  ['producers', 'staff'],     {'fave':'Green'}),
        Candidate('Edgar Equine', 'NY',  ['producers', 'freelance'], {'fave':'Blue' }),
        Candidate('Fern Fack',    'LA',  ['2d',        'staff'],     {'fave':'Blue' }),
    ]

    isFreelance = Check('groups', 'has', 'freelance')

    print 'Test: LA or Sydney, not freelance'
    results = InOffice('LA').Or(InOffice('SYD')).And(Not(isFreelance)).filter(people)
    print show(results)

    print 'Test: Office is not Sydney, or name is Alice'
    results = Check('office','is','SYD').Not().Or(Check('name', 'has', 'Alice')).filter(people)
    print show(results)

    print 'Test: name is Doug, or Fern, or Chuck'
    results = Check('name', 'has', 'Doug').Or(
        Check('name', 'has', 'Fern'),
        Check('name', 'has', 'Chuck')).filter(people)
    print show(results)

if __name__=='__main__':
    tests()
