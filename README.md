# The socialcontext.ai Python client library with CLI

For full reference documentation of the socialcontex.ai API, see the
[API docs](https://api.socialcontext.ai/v1/docs/api)


## Contents

 * Installation
 * Using the client library
 * Using the CLI


## Installation

Client library for the socialcontext.ai web API

```
 $ pip install git+https://github.com/socialcontext-ai/socialcontext.git
```


## Using the client library

### Instantiate a client

```
from socialcontext.api import SocialcontextClient
client = SocialcontextClient(APPLICATION_ID, APPLICATION_SECRET)
```


### List jobs

```
job_list = client.jobs().json()['jobs']
```

### Create a batch classification job

```
job = client.create_job(
    input_file='s3://socialcontext-batches/AcmeInc/Job01/urls.txt.gz',
    output_path='s3://socialcontext-batches/AcmeInc/Job01/',
    models=['antivax', 'provax']
)
```

### Submit the job for execution

```
client.update_job(job['job_id'], action='schedule')
```

### Check the status of the job

Get current info about the job, including:

 * status
 * locations of output files written
 * count of URLs processed
 * count of batches written

```
info = client.jobs(job['job_id']).json()
```

### Cancel the running job

```
client.update_job(job['job_id'], action='cancel')
```

### Delete the job

```
client.delete_job(job['job_id'])
```

## Using the CLI

Client library for the socialcontext.ai web API.

The CLI will read credentials from the environment. Be sure to set these environment
variables:

```
SOCIALCONTEXT_APP_ID
SOCIALCONTEXT_APP_SECRET
```

### Get help for the CLI

In general, see the command line help and subcommand-specific help for details not
covered here.

```
 $ socialcontext --help
 $ socialcontext jobs --help
```

### List supported classification models

```
 $ socialcontext models
```


### List jobs

```
 $ socialcontext jobs list
```

### Create a batch classification job

E.g., a classification job for antivax and provax:

```
 $ socialcontext jobs create s3://socialcontext-batches/AcmeInc/Job01/urls.txt.gz --output-path s3://socialcontext-batches/AcmeInc/Job01/ antivax provax
```

### Submit the job for execution

```
 $ socialcontext jobs run $JOB_ID
```

### Get job info

```
 $ socialcontext jobs info $JOB_ID
```

### Cancel the running job

```
 $ socialcontext jobs cancel $JOB_ID
```

### Delete the job

```
 $ socialcontext jobs delete $JOB_ID
```
