from ..models import Article


from sqlalchemy.orm import joinedload

def get_articles():
    return (
        Article.query
        .options(joinedload(Article.tools))  # 🔥 DAS IST DER FIX
        .order_by(Article.article_no)
        .all()
    )

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

def get_article_logs(article_id):
    return ChangeLog.query.filter_by(
        entity_type="article",
        entity_id=article_id
    ).order_by(ChangeLog.created_at.desc()).all()
