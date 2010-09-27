from gtksourceview2 import CompletionProvider, CompletionProposal
from gtksourceview2 import COMPLETION_ACTIVATION_USER_REQUESTED
import gobject


class Proposal(gobject.GObject, CompletionProposal):
    def __init__(self, proposal):
        gobject.GObject.__init__(self)
        self.proposal = proposal
        
    def do_get_label(self):
        return self.proposal.name

    def do_get_text(self):
        return self.proposal.name
                
                
class RopeCompletionProvider(gobject.GObject, CompletionProvider):
    def __init__(self, editor):
        gobject.GObject.__init__(self)
        self.editor = editor
    
    def do_get_name(self):
        return 'python'
                
    def do_get_priority(self):
        return 1

    def do_set_priority(self):
        pass

    def do_get_activation(self):
        return COMPLETION_ACTIVATION_USER_REQUESTED 

    def do_populate(self, context):
        project = self.editor.project
    
        from rope.contrib import codeassist
        
        try:
            proposals = codeassist.sorted_proposals(
                codeassist.code_assist(project, *self.editor.get_source_and_offset(),
                    resource=self.editor.get_rope_resource(project)))
                    
        except Exception, e:
            import traceback
            traceback.print_exc() 
            return

        context.add_proposals(self, [Proposal(p) for p in proposals], True)
        
gobject.type_register(RopeCompletionProvider)
gobject.type_register(Proposal)
