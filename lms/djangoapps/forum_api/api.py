
from forum_api.mongo import forumMessages

class forumApi(forumMessages):

    def __init__(self,course_id,user_id=None):
         forumMessages.__init__(self,course_id,user_id=user_id)

    def new_post_not_read(self):

        context = {
            "status":False
        }

        if self.user_id is not None:
            excludes_ids = self.is_user_oldest_post()
            new_comments = self.get_courses_comments(exclude = excludes_ids)

            if len(new_comments) > 0:
                context['status'] = True

        return context
