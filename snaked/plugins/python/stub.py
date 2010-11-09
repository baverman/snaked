class RegexObject:
    def __init__(self):
        self.flags = 0
        self.groups = 0
        self.groupindex = {}
        self.pattern = ""

    def match(string, pos=None, endpos=None):
        """If zero or more characters at the beginning of *string* match this regular
        expression, return a corresponding :class:`MatchObject` instance.  Return
        ``None`` if the string does not match the pattern; note that this is different
        from a zero-length match.

        .. note::

           If you want to locate a match anywhere in *string*, use
           :meth:`~RegexObject.search` instead.

        The optional second parameter *pos* gives an index in the string where the
        search is to start; it defaults to ``0``.  This is not completely equivalent to
        slicing the string; the ``'^'`` pattern character matches at the real beginning
        of the string and at positions just after a newline, but not necessarily at the
        index where the search is to start.

        The optional parameter *endpos* limits how far the string will be searched; it
        will be as if the string is *endpos* characters long, so only the characters
        from *pos* to ``endpos - 1`` will be searched for a match.  If *endpos* is less
        than *pos*, no match will be found, otherwise, if *rx* is a compiled regular
        expression object, ``rx.match(string, 0, 50)`` is equivalent to
        ``rx.match(string[:50], 0)``.

           >>> pattern = re.compile("o")
           >>> pattern.match("dog")      # No match as "o" is not at the start of "dog."
           >>> pattern.match("dog", 1)   # Match as "o" is the 2nd character of "dog".
           <_sre.SRE_Match object at ...>

        """
        return MatchObject()

    def search(string, pos=None, endpos=None):
        """Scan through *string* looking for a location where this regular expression
        produces a match, and return a corresponding :class:`MatchObject` instance.
        Return ``None`` if no position in the string matches the pattern; note that this
        is different from finding a zero-length match at some point in the string.

        The optional *pos* and *endpos* parameters have the same meaning as for the
        :meth:`~RegexObject.match` method.
        """

        return MatchObject()

    def split(string, maxsplit=0):
        """Split *string* by the occurrences of *pattern*.

        If capturing parentheses are
        used in *pattern*, then the text of all groups in the pattern are also returned
        as part of the resulting list. If *maxsplit* is nonzero, at most *maxsplit*
        splits occur, and the remainder of the string is returned as the final element
        of the list.  (Incompatibility note: in the original Python 1.5 release,
        *maxsplit* was ignored.  This has been fixed in later releases.)

            >>> re.split('\W+', 'Words, words, words.')
            ['Words', 'words', 'words', '']
            >>> re.split('(\W+)', 'Words, words, words.')
            ['Words', ', ', 'words', ', ', 'words', '.', '']
            >>> re.split('\W+', 'Words, words, words.', 1)
            ['Words', 'words, words.']
        """

    def findall(string, pos=None, endpos=None):
        """Return all non-overlapping matches of *pattern* in *string*, as a list of strings.

        The *string* is scanned left-to-right, and matches are returned in
        the order found.  If one or more groups are present in the pattern, return a
        list of groups; this will be a list of tuples if the pattern has more than
        one group.  Empty matches are included in the result unless they touch the
        beginning of another match.
        """

    def finditer(string, pos=None, endpos=None):
        """Return an :term:`iterator` yielding :class:`MatchObject` instances over all
        non-overlapping matches for the RE *pattern* in *string*.

        The *string* is
        scanned left-to-right, and matches are returned in the order found.  Empty
        matches are included in the result unless they touch the beginning of another
        match.
        """

    def sub(repl, string, count=0):
        r"""Return the string obtained by replacing the leftmost non-overlapping occurrences
        of *pattern* in *string* by the replacement *repl*.  If the pattern isn't found,
        *string* is returned unchanged.  *repl* can be a string or a function; if it is
        a string, any backslash escapes in it are processed.  That is, ``\n`` is
        converted to a single newline character, ``\r`` is converted to a linefeed, and
        so forth.  Unknown escapes such as ``\j`` are left alone.  Backreferences, such
        as ``\6``, are replaced with the substring matched by group 6 in the pattern.
        For example:

          >>> re.sub(r'def\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\(\s*\):',
          ...        r'static PyObject*\npy_\1(void)\n{',
          ...        'def myfunc():')
          'static PyObject*\npy_myfunc(void)\n{'

        If *repl* is a function, it is called for every non-overlapping occurrence of
        *pattern*.  The function takes a single match object argument, and returns the
        replacement string.  For example:

          >>> def dashrepl(matchobj):
          ...     if matchobj.group(0) == '-': return ' '
          ...     else: return '-'
          >>> re.sub('-{1,2}', dashrepl, 'pro----gram-files')
          'pro--gram files'

        The pattern may be a string or an RE object; if you need to specify regular
        expression flags, you must use a RE object, or use embedded modifiers in a
        pattern; for example, ``sub("(?i)b+", "x", "bbbb BBBB")`` returns ``'x x'``.

        The optional argument *count* is the maximum number of pattern occurrences to be
        replaced; *count* must be a non-negative integer.  If omitted or zero, all
        occurrences will be replaced. Empty matches for the pattern are replaced only
        when not adjacent to a previous match, so ``sub('x*', '-', 'abc')`` returns
        ``'-a-b-c-'``.

        In addition to character escapes and backreferences as described above,
        ``\g<name>`` will use the substring matched by the group named ``name``, as
        defined by the ``(?P<name>...)`` syntax. ``\g<number>`` uses the corresponding
        group number; ``\g<2>`` is therefore equivalent to ``\2``, but isn't ambiguous
        in a replacement such as ``\g<2>0``.  ``\20`` would be interpreted as a
        reference to group 20, not a reference to group 2 followed by the literal
        character ``'0'``.  The backreference ``\g<0>`` substitutes in the entire
        substring matched by the RE.
        """

    def subn(repl, string, count=0):
        """Perform the same operation as :func:`sub`, but return a tuple ``(new_string,
        number_of_subs_made)``.
        """

class MatchObject:
    def __init__(self):
        self.pos = 0
        self.endpos = 0
        self.lastindex = 0
        self.lastgroup = ""
        self.re = RegexObject()
        self.string = ""

    def expand(template):
        """Return the string obtained by doing backslash substitution on the template
        string *template*, as done by the :meth:`~RegexObject.sub` method.  Escapes
        such as ``\n`` are converted to the appropriate characters, and numeric
        backreferences (``\1``, ``\2``) and named backreferences (``\g<1>``,
        ``\g<name>``) are replaced by the contents of the corresponding group.
        """

    def group(*groups):
        """
        Returns one or more subgroups of the match.  If there is a single argument, the
        result is a single string; if there are multiple arguments, the result is a
        tuple with one item per argument. Without arguments, *group1* defaults to zero
        (the whole match is returned). If a *groupN* argument is zero, the corresponding
        return value is the entire matching string; if it is in the inclusive range
        [1..99], it is the string matching the corresponding parenthesized group.  If a
        group number is negative or larger than the number of groups defined in the
        pattern, an :exc:`IndexError` exception is raised. If a group is contained in a
        part of the pattern that did not match, the corresponding result is ``None``.
        If a group is contained in a part of the pattern that matched multiple times,
        the last match is returned.

          >>> m = re.match(r"(\w+) (\w+)", "Isaac Newton, physicist")
          >>> m.group(0)       # The entire match
          'Isaac Newton'
          >>> m.group(1)       # The first parenthesized subgroup.
          'Isaac'
          >>> m.group(2)       # The second parenthesized subgroup.
          'Newton'
          >>> m.group(1, 2)    # Multiple arguments give us a tuple.
          ('Isaac', 'Newton')

        If the regular expression uses the ``(?P<name>...)`` syntax, the *groupN*
        arguments may also be strings identifying groups by their group name.  If a
        string argument is not used as a group name in the pattern, an :exc:`IndexError`
        exception is raised.

        A moderately complicated example:

          >>> m = re.match(r"(?P<first_name>\w+) (?P<last_name>\w+)", "Malcom Reynolds")
          >>> m.group('first_name')
          'Malcom'
          >>> m.group('last_name')
          'Reynolds'

        Named groups can also be referred to by their index:

          >>> m.group(1)
          'Malcom'
          >>> m.group(2)
          'Reynolds'

        If a group matches multiple times, only the last match is accessible:

          >>> m = re.match(r"(..)+", "a1b2c3")  # Matches 3 times.
          >>> m.group(1)                        # Returns only the last match.
          'c3'
        """

    def groups(default=None):
        """
        Return a tuple containing all the subgroups of the match, from 1 up to however
        many groups are in the pattern.  The *default* argument is used for groups that
        did not participate in the match; it defaults to ``None``.  (Incompatibility
        note: in the original Python 1.5 release, if the tuple was one element long, a
        string would be returned instead.  In later versions (from 1.5.1 on), a
        singleton tuple is returned in such cases.)

        For example:

          >>> m = re.match(r"(\d+)\.(\d+)", "24.1632")
          >>> m.groups()
          ('24', '1632')

        If we make the decimal place and everything after it optional, not all groups
        might participate in the match.  These groups will default to ``None`` unless
        the *default* argument is given:

          >>> m = re.match(r"(\d+)\.?(\d+)?", "24")
          >>> m.groups()      # Second group defaults to None.
          ('24', None)
          >>> m.groups('0')   # Now, the second group defaults to '0'.
          ('24', '0')
        """

    def groupdict(default):
        """
        Return a dictionary containing all the *named* subgroups of the match, keyed by
        the subgroup name.  The *default* argument is used for groups that did not
        participate in the match; it defaults to ``None``.  For example:

          >>> m = re.match(r"(?P<first_name>\w+) (?P<last_name>\w+)", "Malcom Reynolds")
          >>> m.groupdict()
          {'first_name': 'Malcom', 'last_name': 'Reynolds'}
        """

        return {}

    def start(group=None):
        """Return the indices of the start and end of the substring matched by *group*;
        *group* defaults to zero (meaning the whole matched substring). Return ``-1`` if
        *group* exists but did not contribute to the match.  For a match object *m*, and
        a group *g* that did contribute to the match, the substring matched by group *g*
        (equivalent to ``m.group(g)``) is ::

          m.string[m.start(g):m.end(g)]

        Note that ``m.start(group)`` will equal ``m.end(group)`` if *group* matched a
        null string.  For example, after ``m = re.search('b(c?)', 'cba')``,
        ``m.start(0)`` is 1, ``m.end(0)`` is 2, ``m.start(1)`` and ``m.end(1)`` are both
        2, and ``m.start(2)`` raises an :exc:`IndexError` exception.

        An example that will remove *remove_this* from email addresses:

          >>> email = "tony@tiremove_thisger.net"
          >>> m = re.search("remove_this", email)
          >>> email[:m.start()] + email[m.end():]
          'tony@tiger.net'
        """

    def end(group=None):
        """see :method:`start`"""

    def span(group=None):
        """For :class:`MatchObject` *m*, return the 2-tuple ``(m.start(group),
        m.end(group))``. Note that if *group* did not contribute to the match, this is
        ``(-1, -1)``.  *group* defaults to zero, the entire match.
        """