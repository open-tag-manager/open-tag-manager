from retriever_base import RetrieverBase
import os


class MakePartition(RetrieverBase):
    def __init__(self, **kwargs):
        super(MakePartition, self).__init__(**kwargs)

    def execute(self):
        self.make_partition()


def main():
    make_partition = MakePartition(
        athena_table=os.environ.get('STATS_ATHENA_TABLE'),
        athena_database=os.environ.get('STATS_ATHENA_DATABASE'),
        athena_result_bucket=os.environ.get('STATS_ATHENA_RESULT_BUCKET'),
        athena_result_prefix=os.environ.get('STATS_ATHENA_RESULT_PREFIX') or '',
    )
    make_partition.execute()


if __name__ == '__main__':
    main()
