from jobs import job


@job(
    name="test",
)
def main(test, job_num, **kwargs):

    print(test)
    print(job_num)
    print(kwargs)

    return f"Job: {job_num}"
