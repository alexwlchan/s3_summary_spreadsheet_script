# s3_summary_spreadsheet_script

This repo has a Python script that creates a spreadsheet with a summary of your S3 buckets:

*   How many buckets do I have?
*   How many objects are in each bucket?
*   How many bytes are in each bucket?

The last one is directly tied to your S3 costs, so this script gives you a way to find quick ways to reduce your S3 bill.
Run the script, and then ask yourself **given what I use all my buckets for, are any of them surprisingly large or populous?**



## Usage

You need Python 3, which you can install through most package managers or [from the Python website](https://www.python.org/downloads/).

1.  Install boto3 (the AWS SDK for Python):

    ```console
    $ pip3 install --user boto3
    ```

2.  Set up your AWS config and credentials for boto3.
    (See the instructions [in the boto3 docs](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html?highlight=credentials).)


3.  Clone this repository:

    ```console
    $ git clone https://github.com/alexwlchan/s3_summary_spreadsheet_script.git
    $ cd s3_summary_spreadsheet_script
    ```

4.  Run the script:

    ```console
    $ python3 create_s3_summary_spreadsheet.py
    ✨ Written a summary of your S3 stats to buckets.csv ✨
    ```



## Motivation

I work at [Wellcome Collection][wc].
Whenever I look at our AWS bill, one of the biggest costs is always S3 storage.
That's not a surprise -- our account holds, among other things, two copies of our [entire digital archive], which is nearly 120TB and growing every day.
If we ever got a bill and there *wasn't* a big number next to S3, it's time to panic.

We spend about $25,000 on S3 storage every year.
That's not nothing, but it's also not exorbitant in the context of a large organisation.
**It'd be nice to find some easy wins, but developer time costs money too** -- it's worth an hour to save a few thousand dollars a year, but a complete audit to squeeze out a few extra dollars is out of the question.

I wrote this script to give me a quick overview of our buckets, so see if there were any quick wins.
Among other things, the first time I ran it I discovered:

*   Some leftover files from old experiments that could be deleted
*   A bucket with versioning enabled, where we'd "deleted" all the objects, but the versions were all hanging around
*   A bucket where objects were being saved in the wrong storage class

It took about half an hour to write the initial version, and a few hours more to tidy it up.
I'm sharing it here so other people can use it to find quick wins in their own AWS accounts.

[wc]: https://wellcomecollection.org/
[entire digital archive]: https://stacks.wellcomecollection.org/building-wellcome-collections-new-archival-storage-service-3f68ff21927e



## How it works

The script uses the S3 CloudWatch metrics to determine the size of the bucket.
They're only updated every few days, and may be a bit out-of-date or inaccurate, but that's okay – I'm only using this to get a rough idea of which buckets have an unexpected number of objects.



## License

MIT.



## Say thanks

If you found this useful, you can say thanks [on Twitter](https://twitter.com/alexwlchan), or by donating to [one of the charities I support](https://alexwlchan.net/say-thanks/#donate-to-charity).
