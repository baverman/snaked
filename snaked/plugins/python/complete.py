import textwrap

import weakref

import gtk
from gtksourceview2 import CompletionProvider, CompletionProposal
from gtksourceview2 import COMPLETION_ACTIVATION_USER_REQUESTED

import gobject
from glib import markup_escape_text

def pangonify_rst(text):
    result = ''

    lines = text.strip().expandtabs().splitlines()

    if len(lines) > 1 and lines[1].strip():
        lines = [lines[0]] + [''] + lines[1:]

    indent = 1000
    for l in lines[1:]:
        stripped = l.lstrip()
        if stripped:
            indent = min(indent, len(l) - len(stripped))

    trimmed = [lines[0].strip()]
    if indent < 1000:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())

    wrapper = textwrap.TextWrapper(width=60)
    paragraph = ''
    break_paragraph = False

    def add_paragraph():
        r = result
        if paragraph:
            if break_paragraph:
                r += '\n'

            r += wrapper.fill(paragraph) + '\n\n'
            return r, '', False

        return r, '', break_paragraph

    for l in trimmed:
        if not l.strip():
            result, paragraph, break_paragraph = add_paragraph()
        else:
            if l.startswith('  '):
                result, paragraph, break_paragraph = add_paragraph()
                break_paragraph = True
                result += "<tt>%s</tt>" % markup_escape_text(l)
                result += '\n'
            else:
                paragraph += markup_escape_text(l) + ' '

    if paragraph:
        result, _, _ = add_paragraph()

    return result


class Proposal(gobject.GObject, CompletionProposal):
    def __init__(self, proposal):
        gobject.GObject.__init__(self)
        self.proposal = proposal

    def do_get_label(self):
        return self.proposal.name

    def do_get_text(self):
        return self.proposal.name

    def do_get_info(self):
        info = self.proposal.get_doc()
        if info:
            return pangonify_rst(info)
        else:
            return ''

class RopeCompletionProvider(gobject.GObject, CompletionProvider):
    def __init__(self, plugin):
        gobject.GObject.__init__(self)
        self.plugin = weakref.ref(plugin)
        self.info_widget = gtk.ScrolledWindow()
        self.info_widget.set_size_request(400, 300)
        self.info_widget.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        label = gtk.Label()
        label.set_alignment(0, 0)
        label.set_line_wrap(False)
        self.info_widget.add_with_viewport(label)
        self.info_widget.label = label
        self.info_widget.show_all()

    def do_get_name(self):
        return 'python'

    def do_get_priority(self):
        return 100

    def do_set_priority(self):
        pass

    def do_get_activation(self):
        return COMPLETION_ACTIVATION_USER_REQUESTED

    def do_get_info_widget(self, proposal):
        self.info_widget.label.set_markup(proposal.get_info())
        return self.info_widget

    def do_update_info(self, proposal, info):
        info.get_widget().label.set_markup(proposal.get_info())

    def do_populate(self, context):
        project = self.plugin().project_manager.project
        from rope.contrib import codeassist

        try:
            proposals = codeassist.sorted_proposals(
                codeassist.code_assist(project, *self.plugin().get_source_and_offset(),
                    resource=self.plugin().get_rope_resource(project), maxfixes=3))

        except Exception, e:
            import traceback
            traceback.print_exc()
            self.plugin().editor.message(str(e), 5000)
            return

        if proposals:
            context.add_proposals(self, [Proposal(p) for p in proposals], True)
        else:
            context.add_proposals(self, [], True)
            self.plugin().editor.message("Can't assist")

gobject.type_register(RopeCompletionProvider)
gobject.type_register(Proposal)
