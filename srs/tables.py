import django_tables2 as tables
from django_tables2 import A


class ReplayTable(tables.Table):
    title          = tables.LinkColumn('replay_detail', args=[A('gameID')])
    upload_date    = tables.Column()
    uploader       = tables.Column()
    download_count = tables.Column(accessor="replayfile.download_count")
    comment_count  = tables.Column()
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-upload_date"
