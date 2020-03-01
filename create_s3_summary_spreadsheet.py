#!/usr/bin/env python3

import csv
import datetime

import boto3


def get_bucket_names(s3_client):
    """Returns the name of every bucket in this S3 account."""
    resp = s3_client.list_buckets()

    return [bucket["Name"] for bucket in resp["Buckets"]]


def get_size_of_bucket(cloudwatch_client, *, bucket_name):
    """
    Given the name of a bucket, return a rough estimate for the bytes in this
    bucket per storage class.
    """
    # CloudWatch Metrics has a 'BucketSizeBytes' metric, with one for each storage
    # class.  First use list_metrics to find out what those metrics are (i.e. which
    # storage classes are we using in this bucket?).
    list_metrics_resp = cloudwatch_client.list_metrics(
        Namespace="AWS/S3",
        MetricName="BucketSizeBytes",
        Dimensions=[{"Name": "BucketName", "Value": bucket_name}],
    )

    storage_class_dimensions = [
        metric["Dimensions"] for metric in list_metrics_resp["Metrics"]
    ]

    # This creates a map
    #
    #   "Standard"   -> { ... cloudwatch dimensions for Standard ...}
    #   "StandardIA" -> { ... cloudwatch dimensions for StandardIA ...}
    #
    # When we request metrics from the GetMetricData API, we need to identify
    # each request with an ID.  The storage class name is the ID.
    storage_classes = {
        next(
            dim["Value"] for dim in dimensions if dim["Name"] == "StorageType"
        ): dimensions
        for dimensions in storage_class_dimensions
    }

    # Now we know what storage classes are in use in this bucket, let's go ahead
    # and fetch them.  Note: the S3 Metrics aren't updated that frequently, so
    # we need to pick a fairly long period.
    #
    # Note: we lowercase the storage class name in the ID because it has
    # to start with a lowercase alphabet character.
    storage_class_queries = [
        {
            "Id": name.lower(),
            "MetricStat": {
                "Metric": {
                    "Namespace": "AWS/S3",
                    "MetricName": "BucketSizeBytes",
                    "Dimensions": dimensions,
                },
                "Period": 3 * 24 * 60 * 60,
                "Stat": "Average",
            },
        }
        for name, dimensions in storage_classes.items()
    ]

    number_of_objects_query = [
        {
            "Id": "number_of_objects",
            "MetricStat": {
                "Metric": {
                    "Namespace": "AWS/S3",
                    "MetricName": "NumberOfObjects",
                    "Dimensions": [
                        {"Name": "BucketName", "Value": bucket_name},
                        {"Name": "StorageType", "Value": "AllStorageTypes"},
                    ],
                },
                "Period": 7 * 24 * 60 * 60,
                "Stat": "Average",
            },
        }
    ]

    get_metric_resp = cloudwatch_client.get_metric_data(
        MetricDataQueries=storage_class_queries + number_of_objects_query,
        StartTime=datetime.datetime.now() - datetime.timedelta(days=14),
        EndTime=datetime.datetime.now(),
    )

    # Finally, tidy up the data into a format that's a bit easier to deal
    # with in the calling code.
    rv = {"bucket name": bucket_name}

    for metric_result in get_metric_resp["MetricDataResults"]:

        # The number of objects we pass straight through
        if metric_result["Id"] == "number_of_objects":
            try:
                rv["number of objects"] = int(metric_result["Values"][-1])
            except IndexError:
                rv["number of objects"] = 0

        else:
            # For storage classes, we include the raw number of bytes, and a
            # human-readable storage value.
            storage_class_name = next(
                class_name
                for class_name in storage_classes
                if class_name.lower() == metric_result["Id"]
            )

            rv[storage_class_name] = int(metric_result["Values"][-1])

    return rv


def naturalsize(value):
    # A simplified version of the naturalsize() method in the
    # humanize module: https://pypi.org/project/humanize/
    decimal_suffixes = ("kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")

    base = 1024

    if value == 1:
        return "1 byte"
    elif value < base:
        return "%d bytes" % value

    for i, suffix in enumerate(decimal_suffixes):
        unit = base ** (i + 2)
        if value < unit:
            break
    return "%.1f %s" % ((base * value / unit), suffix)


def write_csv(bucket_sizes):
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_name = f"s3_summary_spreadsheet_{now}.csv"

    storage_names = [
        "StandardStorage",
        "StandardIAStorage",
        "StandardIASizeOverhead",
        "ReducedRedundancyStorage",
        "GlacierStorage",
        "GlacierObjectOverhead",
        "GlacierS3ObjectOverhead",
        "DeepArchiveStorage",
        "DeepArchiveObjectOverhead",
        "DeepArchiveS3ObjectOverhead",
        "DeepArchiveStagingStorage",
    ]

    fieldnames = ["bucket name", "number of objects"]

    for name in storage_names:
        fieldnames.append(f"{name} (bytes)")
        fieldnames.append(f"{name} (human-readable)")

    with open(csv_name, "w") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for bucket in bucket_sizes:
            row = {
                "bucket name": bucket.pop("bucket name"),
                "number of objects": bucket.pop("number of objects"),
            }

            for storage_class, byte_count in bucket.items():
                row[f"{storage_class} (bytes)"] = byte_count
                row[f"{storage_class} (human-readable)"] = naturalsize(byte_count)

            writer.writerow(row)

    return csv_name


if __name__ == "__main__":
    s3_client = boto3.client("s3")
    cloudwatch_client = boto3.client("cloudwatch")

    bucket_names = get_bucket_names(s3_client)

    bucket_sizes = [
        get_size_of_bucket(cloudwatch_client, bucket_name=name) for name in bucket_names
    ]

    csv_name = write_csv(bucket_sizes)
    print(f"✨ Written a summary of your S3 stats to {csv_name} ✨")
