# Introduction
This guide details how to use the custom `manage.py` shell commands. All
commands can be invoked using the shell command format:

```shell script
python manage.py <command name> --settings=settings.<your settings module>
```

You can omit the settings argument to use the default settings module (the
module imported in `mavedb/settings.py`).


# createlicences
This command expects the file `data/main/licenes.json` and folder
`data/main/licence_legal_code` containing the licence text for your licences.
The `licences.json` file should follow the format below:

```json
{
  "licences": [
    {
      "short_name": "CC0",
      "long_name": "CC0 (Public domain)",
      "legal_code": {
        "file": true,
        "value": "CC0.txt"
      },
      "logo": "cc-zero.svg",
      "link": "https://creativecommons.org/publicdomain/zero/1.0/",
      "version": "1.0"
    },
    {
      "short_name": "Other - See Data Usage Guidelines",
      "long_name": "Other - See Data Usage Guidelines",
      "legal_code": {
        "file": false,
        "value": "See Data Usage Guidelines"
      },
      "logo": "",
      "link": "",
      "version": "1.0"
    }
  ]
}
```

This file specifies a list of licences to create/update. This command has no
arguments. Existing licences matching `short_name` in the json file will be
updated.


# createreferences
This command expects the file `data/genome/reference_genomes.json` The
`reference_genomes.json` file should follow the format below:

```json
[
    {
        "assembly_identifier": {
            "dbname": "GenomeAssembly",
            "dbversion": null,
            "identifier": "GCF_000001405.10",
            "url": "http://www.ncbi.nlm.nih.gov/assembly/GCF_000001405.10"
        },
        "short_name": "hg16",
        "organism_name": "Homo sapiens"
    },
    {
        "assembly_identifier": null,
        "short_name": "Synthetic",
        "organism_name": "Synthetic sequence"
    }
]
```

This file specifies a list of reference genomes to create/update. This command
has no arguments. Only entries with a `short_name` that does not exist will be
created. Existing instances will not be updated since other models rely on the
`ReferenceGenome` table.


# savereferences
This command will serialize the `ReferenceGenome` models into
`data/genome/reference_genomes.json`. It will overwrite any existing file. This
command accepts no arguments.


# updatesiteinfo
Invoke this command to updat the `SiteInformation` singleton row. It expects
the file `data/main/site_info.json` to exist with the following format:

```json
{
    "branch": "",
    "md_about": "about.md",
    "md_citation": "",
    "md_documentation": "userdocs.md",
    "md_privacy": "",
    "md_terms": "",
    "md_usage_guide": "",
    "version": "1.6.3-beta"
}
```

You can specify markdown files on fields with the `md_` prefix (must be saved
in the same directory as the JSON file) to set as the field text. This command
accepts no arguments.


# savesiteinfo
This command will serialize the `SiteInformation` singleton into
`data/main/site_info.json`. It will overwrite any existing file. This command
accepts no arguments.


# geterror
This command displays a detailed celery error for a given `task_id` and `username`.
The `username` specifies the submitting user's ORCID. This command must be
invoked as:

```shell script
python manage.py geterror --task_id=<task-uuid> --username=<ORCID>
```


# renamegroups
This command renames the contributor groups for all `ScoreSets`, `ExperimentSets`
and `Experiments`. It was used to correct a naming bug in production so it should
not be necessary to run this again. This command accepts no arguments.


# renumber
This command renumbers the `Variants` in a `ScoreSet` starting from 1. It was
used to correct a numbering bug in production so it should not be necessary to
run this again. This command must be invoked as:

```shell script
python manage.py renumber --urns=<space separated urns> --all
```

Specify a list of space-separated urns to correct, or alternatively set the
boolean flag `--all` to correct all `ScoreSets`.


# savesitestats
Export a gzipped tarball containing site page view statistics. Specify an
absolute save path with the `--path` argument.


# setprivate
Set a `ScoreSet`, `Experiment` or `ExperimentSet` as private. It is recommended
that it is used only on `ScoreSet` models. Settings parent models as private
will not alter child models. This could create strange behaviour such as not
being able to view the parent of a public child. Invoke the command as:

```shell script
python manage.py setprivate --urn=<model-urn>
```

# setstate
Set a the celery state of a `ScoreSet`. Invoke the command as:

```shell script
python manage.py setprivate --urn=<model-urn> --state=<state text>
```

The `state` argument will accept the values `processing`, `failed` or `success`.


# createnews
Create a news item for the landing page. Invoke the command as:

```shell script
python manage.py createnews --message=<string message> --level=<string level>
```

The `message` argument can specify a string message or a markdown file. The
`level` argument can take the values `Critical`, `Important`, `Information`,
`Happy holidays` or `April fools`.


# createtestentries
For development purposes to seed the database with test entries. Also creates
test users with the password `1234qwer` and username `user-<number>` where
number ranges from 1 to 40.


# createdefaultsecrets
Creates a default secrets json file. Used by settings module to create a secrets
file if one does not exist. This should not be called directly.


# cleanusers
Deletes accounts with malicious looking usernames. Pass `--commit` to commit changes, otherwise
it is run in dry mode and will only list accounts that will be deleted. Pass a list of comma separated
usernames via `--exclude` to ignore these associated accounts.
