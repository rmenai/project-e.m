<br />
<p align="center">
  <a href="https://github.com/rmenai/project-e.m">
    <img src="https://avatars.githubusercontent.com/u/89700626?v=4&s=160" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">Project E.M</h3>

  <p align="center">
    Awesome project-e.m created by rmenai
    <br />
    <a href="https://github.com/rmenai/project-e.m"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/rmenai/project-e.m">View Demo</a>
    ·
    <a href="https://github.com/rmenai/project-e.m/issues/new?assignees=&labels=&template=bug_report.md&title=">Report Bug</a>
    ·
    <a href="https://github.com/rmenai/project-e.m/issues/new?assignees=&labels=&template=feature_request.md&title=">Request Feature</a>
  </p>

<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#installation">Installation</a>
      <ul>
        <li><a href="#using-docker">Using Docker</a></li>
        <li><a href="#for-development">For development</a></li>
      </ul>
    </li>
    <li>
      <a href="#environment-variables">Environment Variables</a>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->

## About The Project

Awesome project-e.m created by rmenai.

<!-- INSTALLATION -->

## Installation

The first step will be to clone the repo

```shell
git clone https://github.com/rmenai/project-e.m.git
```

### Using Docker

Using Docker is generally recommended (but not strictly required) because it abstracts away some additional set up work.

The requirements for Docker are:

* [Docker CE](https://docs.docker.com/install/)

### For development

The requirements are:

* [Python](https://www.python.org/downloads/) and [Poetry](https://python-poetry.org/docs/)

1. Install the dependencies
   ```shell
   poetry install
   ```

## Environment Variables

To run this project, you will need to add the following environment variables to your .env file.

| Variable       | Description                | Default    |
|----------------|----------------------------|------------|
| BOT_NAME       | The name of the bot        | "Bot"      |
| BOT_TOKEN      | The token of the bot       | * Required |
| CHANNEL_DEVLOG | The devlog channel id      | 0          |
| DEBUG          | Toggles debug mode         | False      |
| DEV_GUILD_IDS  | The dev servers of the bot | []         |
| GUILD_IDS      | The servers of the bot     | * Required |
| ROLE_ADMIN     | The admin role name        | "Admin" |
| ROLE_EVERYONE  | The everyone role name     | "@everyone" |

<!-- USAGE EXAMPLES -->

## Usage

Now you are done! You can run the project using

```shell
poetry run task start
```

## Contributing

See [CONTRIBUTING.md](https://github.com/rmenai/project-e.m/blob/main/CONTRIBUTING.md) for ways to get started.

<!-- LICENSE -->

## License

Distributed under the MIT License. See [LICENSE](https://github.com/rmenai/project-e.m/blob/main/LICENSE) for more information.
