# About 
MaveDB is a biological database for Multiplex Assays of Variant Effect (MAVE)
datasets. The primary installation of MaveDB is located at
https://www.mavedb.org. For more information about MaveDB or to cite MaveDB
please refer to the
[MaveDB paper in *Genome Biology*](https://doi.org/10.1186/s13059-019-1845-6).

 MaveDB was developed using Python 3.6, but should be compatible with
 any later Python 3 version. Python 2 is not supported. Running MaveDB requires
 the following software packaged via [Docker](https://www.docker.com/):

 - [Python 3](https://www.python.org/downloads/)
 - [PostgreSQL 9.6](https://www.postgresql.org/about/)
 - [Pandoc 1.9](https://pandoc.org/releases.html#pandoc-1.19.2.4-10-sep-2017)
 - [Erlang](http://www.rabbitmq.com/which-erlang.html) (required by RabbitMQ)
 - [RabbitMQ](http://www.rabbitmq.com/download.html) 

 User authentication with OAuth and ORCID iD requires additional setup and may 
 not be suitable for a local development server. See the 
 [ORCID API documentation](https://members.orcid.org/api/oauth) for a 
 description of OAuth and detailed instructions.

See [MaveDB Development](./FOR_DEVS.md) for a detailed guide on getting up and 
running locally.

See [MaveDB Deployment](./DEPLOYMENT.md) for a detailed production deployment 
guide.

See [MaveDB Admin](./FOR_ADMINS.md) for a guide on custom management commands.