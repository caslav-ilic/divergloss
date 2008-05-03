# -*- coding: UTF-8 -*-

"""
Construct the glossary out of XML document.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import copy
import random
from lxml import etree

from dg.dset import Dset
from dg.util import p_
from dg.util import error, warning
from dg.util import lstr
from dg import _dtd_dir


def from_file (dgfile, validate=True):

    try:
        # Do not validate at parse time, but afterwards.
        # Must resolve xincludes beforehand.
        parser = etree.XMLParser(dtd_validation=False, remove_comments=True)
        tree = etree.parse(dgfile, parser=parser)
        tree.xinclude()
    except (etree.XMLSyntaxError, etree.XIncludeError), e:
        errlins = "\n".join([str(x) for x in list(e.error_log)])
        error(p_("error message",
                 "XML parsing failed:\n"
                 "%(msg)s") % {"msg":errlins})

    if validate:
        # Work around a bug: non-unique identifiers do not produce any
        # message when validation fails.
        ids = tree.xpath("//*/@id")
        iddict = {}
        for id in ids:
            if id in iddict:
                # Keep the message format same as below, just report ids.
                error(p_("error message",
                         "DTD validation failed:\n"
                         "%(msg)s") % {"msg":p_("error message",
                                                "duplicate ID '%(id)s'")
                                             % {"id": id}})
            iddict[id] = True

        # Resolve the DTD file and validate the tree according to it.
        # FIXME: Better determination of dtd file (by public ID, etc.)
        dtdfile = os.path.join(_dtd_dir, tree.docinfo.system_url)
        dtd = etree.DTD(dtdfile)
        if not dtd.validate(tree):
            errlins = "\n".join([str(x) for x in list(dtd.error_log)])
            error(p_("error message",
                     "DTD validation failed:\n"
                     "%(msg)s") % {"msg":errlins})

    # Construct glossary from the document tree.
    gloss = from_tree(tree, validate=validate)

    return gloss


def from_tree (tree, validate=True):

    root = tree.getroot()
    gloss = Glossary(root)

    # Post-DTD validation.
    if validate:
        _post_dtd_validate(gloss)

    return gloss

# --------------------------------------
# Validation.

def _post_dtd_validate (gloss):

    _post_dtd_in_node(gloss, gloss)


def _post_dtd_in_node (gloss, gnode):

    # Do checks.
    _post_dtd_check_keys(gloss, gnode)

    # Traverse further.
    for obj in gnode.__dict__.values():
        if isinstance(obj, Text):
            _post_dtd_in_text(gloss, obj)
        else:
            subns = []
            if isinstance(obj, Gnode):
                subns = [obj]
            elif isinstance(obj, Dset):
                subns = obj.get_all() # all in Dset are Gnode
            elif isinstance(obj, dict):
                subns = [x for x in obj.values() if isinstance(x, Gnode)]
            elif isinstance(obj, list):
                subns = [x for x in obj if isinstance(x, Gnode)]

            for subn in subns:
                _post_dtd_in_node(gloss, subn)


def _post_dtd_in_text (gloss, text):

    # Do checks.
    _post_dtd_check_keys(gloss, text)

    # Traverse further.
    for seg in text:
        if isinstance(seg, Text):
            _post_dtd_in_text(gloss, seg)


def _post_dtd_check_keys (gloss, gnode):

    _post_dtd_ch_key(gloss, gnode, "lang", gloss.languages,
        p_("error message",
           "attribute '%(att)s' states a non-language key: %(key)s"))

    _post_dtd_ch_keyseq(gloss, gnode, "env", gloss.environments,
        p_("error message",
           "attribute '%(att)s' states non-environment keys: %(keys)s"))

    _post_dtd_ch_key(gloss, gnode, "by", gloss.editors,
        p_("error message",
           "attribute '%(att)s' states a non-editor key: %(key)s"))

    _post_dtd_ch_key(gloss, gnode, "src", gloss.sources,
        p_("error message",
           "attribute '%(att)s' states a non-source key: %(key)s"))

    _post_dtd_ch_key(gloss, gnode, "gr", gloss.grammar,
        p_("error message",
           "attribute '%(att)s' states a non-grammar key: %(key)s"))

    _post_dtd_ch_key(gloss, gnode, "root", gloss.extroots,
        p_("error message",
           "attribute '%(att)s' states a non-root key: %(key)s"))

    _post_dtd_ch_key(gloss, gnode, "c", gloss.concepts,
        p_("error message",
           "attribute '%(att)s' states a non-concept key: %(key)s"))

    _post_dtd_ch_keyseq(gloss, gnode, "closeto", gloss.environments,
        p_("error message",
           "attribute '%(att)s' states non-environment keys: %(keys)s"))

    _post_dtd_ch_keyseq(gloss, gnode, "topic", gloss.topics,
        p_("error message",
           "attribute '%(att)s' states non-topic keys: %(keys)s"))

    _post_dtd_ch_keyseq(gloss, gnode, "level", gloss.levels,
        p_("error message",
           "attribute '%(att)s' states non-level keys: %(keys)s"))

    _post_dtd_ch_keyseq(gloss, gnode, "related", gloss.concepts,
        p_("error message",
           "attribute '%(att)s' states non-concept keys: %(keys)s"))


def _post_dtd_ch_key (gloss, gnode, attname, keydict, msg):

    key = getattr(gnode, attname, None)
    if key is not None and key not in keydict:
        _post_dtd_error(gloss, gnode, msg % {"att":attname, "key":key})


def _post_dtd_ch_keyseq (gloss, gnode, attname, keydict, msg):

    keys = getattr(gnode, attname, [])
    if keys is None:
        keys = []
    badkeys = [x for x in keys if x not in keydict and x is not None]
    if badkeys:
        fmtk = " ".join(badkeys)
        _post_dtd_error(gloss, gnode, msg % {"att":attname, "keys":fmtk})


def _post_dtd_error (gloss, gnode, msg):

    lmsg = p_("message with the location it speaks of",
              "%(file)s:%(line)s: %(msg)s") \
           % {"file":gnode.src_file, "line":gnode.src_line, "msg":msg,}

    error(p_("error message",
             "post-DTD validation failed:\n"
             "%(msg)s") % {"msg":lmsg})


# --------------------------------------
# XML extractors.

def _attval (node, attname, defval=None):

    if node is None:
        return defval
    return node.attrib.get(attname, defval)


def _attkey (node, attname):

    key = _attval(node, attname)
    if key is not None:
        key = key.strip()
    return key


def _child_els_by_tag (node, tags, defnodes=[]):

    if node is None:
        return defnodes
    if isinstance(tags, (str, unicode)):
        tags = (tags,)

    selnodes = [x for x in node if x.tag in tags]
    if not selnodes:
        return defnodes
    return selnodes


def _text_segments (seg_node, exp_tags):

    if seg_node is None:
        return []

    segs = []
    if seg_node.text:
        segs.append(seg_node.text)
    for node in seg_node:
        if node.tag in exp_tags:
            segs.append(_tseg_name_type[node.tag](node))
        else:
            segs.append(_pure_text(node))
        if node.tail:
            segs.append(node.tail)

    return segs


def _pure_text (string_node):

    if string_node is None:
        return ""

    s = string_node.text
    for node in string_node:
        s += _pure_text(node) + node.tail

    return s


# --------------------------------------
# Content constructors.

def _content (obj, gloss, node, parse_bundles):

    for consf, args in parse_bundles:
        consf(obj, gloss, node, *args)


def _attributes (obj, gloss, node, attspecs):

    for attspec in attspecs:
        if isinstance(attspec, tuple):
            attname, defval = attspec
        else:
            attname, defval = attspec, None
        if node is not None:
            val = _attval(node, attname, defval)
        else:
            val = defval
        obj.__dict__[attname] = val


def _attrib_lists (obj, gloss, node, attspecs):

    for attspec in attspecs:
        if isinstance(attspec, tuple):
            attname, deflst = attspec
        else:
            attname, deflst = attspec, []
        if node is not None:
            val = _attval(node, attname, deflst)
        else:
            val = deflst
        if isinstance(val, (str, unicode)):
            val = val.split()
        obj.__dict__[attname] = val


def _child_dsets (obj, gloss, node, chdspecs, parent=None):

    for chdspec in chdspecs:
        if len(chdspec) == 3:
            attname, subtype, tagnames = chdspec
        else:
            attname, subtype = chdspec
            tagnames = (attname,)
        if attname not in obj.__dict__:
            obj.__dict__[attname] = Dset(gloss, parent)
        dst = obj.__dict__[attname]
        if node is not None:
            for cnode in _child_els_by_tag(node, tagnames):
                subobj = subtype(gloss, cnode)
                # Add several resolved objects if any embedded selections.
                for rsubobj in _res_embsel(gloss, subobj):
                    dst.add(rsubobj)


def _child_lists (obj, gloss, node, chlspecs):

    for chlspec in chlspecs:
        if len(chlspec) == 3:
            attname, subtype, tagnames = chlspec
        else:
            attname, subtype = chlspec
            tagnames = (attname,)
        if attname not in obj.__dict__:
            obj.__dict__[attname] = []
        lst = obj.__dict__[attname]
        if node is not None:
            for cnode in _child_els_by_tag(node, tagnames):
                lst.append(subtype(gloss, cnode))


def _child_dicts (obj, gloss, node, chmspecs):

    for dictname, subtype, tagname in chmspecs:
        if dictname not in obj.__dict__:
            obj.__dict__[dictname] = {}
        dct = obj.__dict__[dictname]
        if node is not None:
            for cnode in _child_els_by_tag(node, tagname):
                o = subtype(gloss, cnode)
                dct[o.id] = o


def _children (obj, gloss, node, chspecs):

    for chspec in chspecs:
        if len(chspec) == 3:
            attname, subtype, tagnames = chspec
        else:
            attname, subtype = chspec
            tagnames = (attname,)
        if node is not None:
            for cnode in _child_els_by_tag(node, tagnames):
                obj.__dict__[attname] = subtype(gloss, cnode)
                break # a single node expected, so take first
        else:
            obj.__dict__[attname] = None


def _text (obj, gloss, node):

    obj.text = Text(node)


# --------------------------------------
# Self-constructing glossary from XML nodes.

# Base of glossary nodes.
class Gnode:

    def __init__ (self, node=None):

        self.src_line = 0
        self.src_file = "<unknown>"
        if node is not None:
            self.src_line = node.sourceline
            # self.src_file = ?


# Glossary.
class Glossary (Gnode):

    def __init__ (self, node=None):

        Gnode.__init__(self, node)

        _content(self, self, node,
                 [(_attributes,
                   [["id",
                     "lang"]]),
                  (_attrib_lists,
                   [[("env")]])])

        for md_node in _child_els_by_tag(node, "metadata", [None]):
            _content(self, self, md_node,
                     [(_child_dsets,
                       [[("title", Title),
                         ("desc", Desc, ("desc", "ldesc")),
                         ("version", Version)]]),
                      (_children,
                       [[("date", OnlyText)]])])

        for kd_node in _child_els_by_tag(node, "keydefs", [None]):
            for chmspec in [("languages", Language, "language"),
                            ("environments", Environment, "environment"),
                            ("editors", Editor, "editor"),
                            ("sources", Source, "source"),
                            ("topics", Topic, "topic"),
                            ("levels", Level, "level"),
                            ("grammar", Gramm, "gramm"),
                            ("extroots", Extroot, "extroot")]:
                for kds_node in _child_els_by_tag(kd_node, chmspec[0], [None]):
                    _content(self, self, kds_node,
                             [(_child_dicts, [[chmspec]])])

        # Concepts must be parsed after keydefs,
        # e.g. for proper resolution of embedded selectors.
        for cn_node in _child_els_by_tag(node, "concepts", [None]):
            _content(self, self, cn_node,
                     [(_child_dicts, [[("concepts", Concept, "concept")]])])


class Language (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [["id"]]),
                  (_child_dsets,
                   [[("name", Name),
                     ("shortname", Shortname)]])])


class Environment (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [["id"]]),
                  (_attrib_lists,
                   [["closeto"]]),
                  (_child_dsets,
                   [[("name", Name),
                     ("shortname", Shortname),
                     ("desc", Desc, ("desc", "ldesc"))]])])

        # Make no-environment close to all defined environments.
        self.closeto.append(None)


class Editor (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [["id"]]),
                  (_child_dsets,
                   [[("name", Name),
                     ("shortname", Shortname),
                     ("affiliation", Affiliation),
                     ("desc", Desc, ("desc", "ldesc"))]]),
                  (_children,
                   [[("email", OnlyText)]])])


class Source (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [["id"]]),
                  (_child_dsets,
                   [[("name", Name),
                     ("shortname", Shortname),
                     ("desc", Desc, ("desc", "ldesc"))]]),
                  (_children,
                   [[("url", OnlyText),
                     ("email", OnlyText)]])])


class Topic (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [["id"]]),
                  (_child_dsets,
                   [[("name", Name),
                     ("shortname", Shortname),
                     ("desc", Desc, ("desc", "ldesc"))]])])


class Level (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [["id"]]),
                  (_child_dsets,
                   [[("name", Name),
                     ("shortname", Shortname),
                     ("desc", Desc, ("desc", "ldesc"))]])])


class Gramm (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [["id"]]),
                  (_child_dsets,
                   [[("name", Name),
                     ("shortname", Shortname),
                     ("desc", Desc, ("desc", "ldesc"))]])])


class Extroot (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [["id"]]),
                  (_child_dsets,
                   [[("name", Name),
                     ("shortname", Shortname),
                     ("desc", Desc, ("desc", "ldesc"))]]),
                  (_children,
                   [[("rooturl", OnlyText),
                     ("browseurl", OnlyText)]])])


class Concept (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [["id"]]),
                  (_attrib_lists,
                   [["topic",
                     "level",
                     "related"]]),
                  (_child_dsets,
                   [[("desc", Desc, ("desc", "ldesc")),
                     ("term", Term, ("term", "eterm")),
                     ("details", Details),
                     ("media", Media),
                     ("origin", Origin, ("origin", "lorigin")),
                     ("comment", Comment, ("comment", "lcomment"))]])])


class Term (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang),
                     "by",
                     "src",
                     "gr"]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]])])

        if _child_els_by_tag(node, "nom"):
            _content(self, gloss, node,
                     [(_child_dsets,
                       [[("origin", Origin, ("origin", "lorigin")),
                         ("comment", Comment, ("comment", "lcomment"))],
                        self]),
                      (_child_lists,
                       [[("decl", Decl)]]),
                      (_children,
                       [[("nom", OnlyText),
                         ("stem", OnlyText)]])])
        else:
            self.nom = OnlyText(gloss, node)


class Title (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang)]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]]),
                  (_text,
                   [])])


class Version (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang)]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]]),
                  (_text,
                   [])])


class Name (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang)]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]]),
                  (_text,
                   [])])


class Shortname (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang)]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]]),
                  (_text,
                   [])])


class Affiliation (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang)]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]]),
                  (_text,
                   [])])


class Desc (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang),
                     "by",
                     "src"]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]]),
                  (_text,
                   [])])


class Origin (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang),
                     "by"
                     "src"]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]]),
                  (_text,
                   [])])


class Comment (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang),
                     "by"]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]]),
                  (_text,
                   [])])


class Details (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang),
                     "by",
                     "root",
                     "rel"]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]]),
                  (_text,
                   [])])


class Media (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [[("lang", gloss.lang),
                     "by",
                     "root",
                     "rel"]]),
                  (_attrib_lists,
                   [[("env", gloss.env)]]),
                  (_text,
                   [])])


class Decl (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_attributes,
                   [["gr"]]),
                  (_text,
                   [])])


class OnlyText (Gnode):

    def __init__ (self, gloss, node=None):

        Gnode.__init__(self, node)

        _content(self, gloss, node,
                 [(_text,
                   [])])


# Text.
# Organized as a list of structured text segments,
# where the basic segment is plain string.

class Text (list, Gnode): # base class for all in-text elements

    def __init__ (self, node=None, tags=None):

        Gnode.__init__(self, node)

        if tags is None:
            tags = ["para", "ref", "em", "ol"]

        self.extend(_text_segments(node, tags))


class Para (Text):

    def __init__ (self, node=None):

        Text.__init__(self, node, ["ref", "em", "ol"])


class Ref (Text):

    def __init__ (self, node=None):

        Text.__init__(self, node, ["em", "ol"])
        self.c = _attkey(node, "c")


class Em (Text):

    def __init__ (self, node=None):

        Text.__init__(self, node, ["ref", "em", "ol"])


class Ol (Text):

    def __init__ (self, node=None):

        Text.__init__(self, node, ["ref", "em", "ol"])
        self.lang = _attkey(node, "lang")


# Map between text segment types and their tag names.
# Used in _text_segments()
_tseg_name_type = {"para":Para, "ref":Ref, "em":Em, "ol":Ol}


# Resolving of embedded selectors.

# Based on the given object with embedded selectors,
# return list of objects with different languages/environments,
# and the text in them resolved accordingly.
def _res_embsel (gloss, obj):

    if not (hasattr(obj, "text") and hasattr(obj, "env")):
        return [obj]

    # Normalize text: each embedded selector is turned into its own segment
    # of the text, a dictionary of env/string;
    # all encountered environments are reported.
    ntext, envs = _res_embsel_norm_text(obj.text)
    if not envs:
        return [obj]

    # Add object's own environment to encountered environments.
    envs.update(set(obj.env))

    # Create a version of the object for each of the environments.
    robjs = []
    for env in envs:
        # Piece up the best version of text for current environment.
        text = _res_embsel_best_text(gloss, ntext, env)

        # Create object with this environment and text.
        robj = copy.deepcopy(obj)
        robj.env = [env]
        robj.text = text
        robjs.append(robj)

    return robjs


def _res_embsel_norm_text (text):

    ntext = copy.copy(text)
    ntext[:] = []
    envs = set()

    for seg in text:
        if isinstance(seg, Text):
            # Sublist of segments.
            subntext, subenvs = _res_embsel_norm_text(seg)
            ntext.append(subntext)
            envs.update(subenvs)
        else:
            if "~" in seg:
                # Split each embedded selector into an env/string dictionary.
                locntext, locenvs = _res_embsel_parse_one(seg)
                ntext.extend(locntext)
                envs.update(locenvs)
            else:
                # A clean string.
                ntext.append(seg)

    return ntext, envs


def _res_embsel_parse_one (seg):

    ntext = Text()
    envs = set()

    p1 = seg.find("~")
    p2 = -1

    while p1 >= 0:
        head = seg[p2+1:p1]
        if head:
            ntext.append(head)
        p2 = seg.find("~", p1 + 1)
        if p2 < 0:
            warning(p_("warning message",
                       "unterminated embedded selector '%(esel)s'")
                    % {"esel":seg})
            p2 = p1 - 1
            break

        envsegs = {}
        locenvs = set()
        for eseg in seg[p1+1:p2].split("|"):
            pc = eseg.find(":")
            if pc >= 0:
                cenvs = eseg[:pc].split()
                cseg = eseg[pc+1:]
            else:
                cenvs = []
                cseg = eseg

            repenvs = locenvs.intersection(cenvs)
            if repenvs:
                fmtes = " ".join([str(x) for x in list(repenvs)])
                warning(p_("warning message",
                           "segment '%(eseg)s' in embedded selector "
                           "'%(esel)s' repeats environments: %(envs)s")
                        % {"esel":seg, "eseg":eseg, "envs":fmtes})

            locenvs.update(cenvs)
            for cenv in cenvs:
                envsegs[cenv] = cseg

        # Add embedded selector string under a dummy environment,
        # needed later for error reporting.
        envsegs["_esel_"] = seg

        ntext.append(envsegs)
        envs.update(locenvs)

        p1 = seg.find("~", p2 + 1)

    tail = seg[p2+1:]
    if tail:
        ntext.append(tail)

    return ntext, envs


def _res_embsel_best_text (gloss, ntext, env):

    text = copy.copy(ntext)
    text[:] = []
    for seg in ntext:
        if isinstance(seg, Text):
            text.append(_res_embsel_best_text(gloss, seg, env))
        elif isinstance(seg, dict):
            # Try first direct match for environment.
            if env in seg:
                text.append(seg[env])
            else:
                # Try a close environment.
                found_close = False
                if env in gloss.environments:
                    for cenv in gloss.environments[env].closeto:
                        if cenv in seg:
                            text.append(seg[cenv])
                            found_close = True
                            break

                # Take a best shot.
                if not found_close:
                    if env not in gloss.env:
                        warning(p_("warning message",
                                   "no resolution for expected environment "
                                   "'%(env)s' in embedded selector '%(esel)s'")
                                % {"env":env, "esel":seg["_esel_"]})
                    # Pick at random.
                    text.append(random.choice(seg.values()))
        else:
            text.append(seg)

    return text

