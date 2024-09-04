from jobs import job


@job(
    name="test",
)
def main(test, **kwargs):

    print(test)
    print(kwargs)

    return "test"
