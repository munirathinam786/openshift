# OpenShift SRE Console

The repository now includes the full OpenShift SRE application under `openshift-sre/`.

That folder contains the complete runtime:

- FastAPI backend
- MkDocs operator site
- interactive SRE consoles
- MariaDB-backed history storage
- Podman compose workflow
- tests, scripts, and UI source

## Where the code lives

- Application root: `openshift-sre/`
- Runtime source: `openshift-sre/src/aws_sre_agent/`
- Operator docs and consoles: `openshift-sre/docs/`
- Container workflow: `openshift-sre/compose.yaml` and `openshift-sre/Containerfile`

## Run it on port 8000

From the repository root, switch into the app folder and start the stack:

```bash
cd openshift-sre
podman compose up -d --build
```

The OpenShift SRE application is configured to serve on port `8000`.

## Open the console

- [Launch the Agent Console](http://localhost:8000/docs/console.html)
- [Launch the Troubleshooting Console](http://localhost:8000/docs/troubleshooting.html)
- [Launch the Security Console](http://localhost:8000/docs/security-console.html)
- [Open the SRE home page](http://localhost:8000/docs/)

## Operator note

The repository's main documentation preview also commonly uses port `8000`, so run one local stack at a time on that port.

If you want the SRE console live, start it from `openshift-sre/` and use the links above.
