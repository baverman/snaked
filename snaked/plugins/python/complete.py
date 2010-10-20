import re

from gtksourceview2 import CompletionProvider, CompletionProposal
from gtksourceview2 import COMPLETION_ACTIVATION_USER_REQUESTED

import gobject
from glib import markup_escape_text

pydoc_converter = re.compile(r'([^\n])\n[ \t]*?([^\n])')


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
            return markup_escape_text(pydoc_converter.sub(r'\1 \2', info))
        else:
            return ''                
                
class RopeCompletionProvider(gobject.GObject, CompletionProvider):
    def __init__(self, plugin):
        gobject.GObject.__init__(self)
        self.plugin = plugin
    
    def do_get_name(self):
        return 'python'
                
    def do_get_priority(self):
        return 1

    def do_set_priority(self):
        pass

    def do_get_activation(self):
        return COMPLETION_ACTIVATION_USER_REQUESTED 

    def do_populate(self, context):
        project = self.plugin.project
    
        from rope.contrib import codeassist
        
        try:
            proposals = codeassist.sorted_proposals(
                codeassist.code_assist(project, *self.plugin.get_source_and_offset(),
                    resource=self.plugin.get_rope_resource(project), maxfixes=3))
                    
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.plugin.editor.message(str(e), 5000) 
            return

        if proposals:
            context.add_proposals(self, [Proposal(p) for p in proposals], True)
        else:
            context.add_proposals(self, [], True)
            self.plugin.editor.message("Can't assist")
        
gobject.type_register(RopeCompletionProvider)
gobject.type_register(Proposal)
