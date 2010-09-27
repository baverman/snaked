from gtksourceview2 import CompletionProvider, CompletionItem, completion_item_new_from_stock
from gtksourceview2 import COMPLETION_ACTIVATION_USER_REQUESTED
import gobject


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

    def do_match(self, context):
        return context.get_activation() == COMPLETION_ACTIVATION_USER_REQUESTED 

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

        props = []
        for p in proposals:
            props.append(completion_item_new_from_stock(p.name, p.name, 'About', ''))
        
        context.add_proposals(self, props, True)
        
gobject.type_register(RopeCompletionProvider)
