from ..models import Article
from factoryos.core.models.change_log import ChangeLog   # 🔥 DAS FEHLT



from sqlalchemy.orm import joinedload

def get_articles():
    return (
        Article.query
        .options(joinedload(Article.tools))  # 🔥 DAS IST DER FIX
        .order_by(Article.article_no)
        .all()
    )
    
def get_article(article_id):
    return Article.query.get_or_404(article_id)

def search_articles(search=None):

    query = Article.query

    if search:
        query = query.filter(
            Article.article_no.contains(search) |
            Article.article_name.contains(search)
        )

    return query.order_by(Article.article_no).all()


def get_statuses():

    return [
        "active",
        "inactive"
    ]

