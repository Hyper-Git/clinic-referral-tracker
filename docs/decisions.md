# Architecture Decision Records

## ADR-001: Run the project in a dedicated development account.
We run the project in the development member account, not the management account, because the management account should only be used to manage the other accounts. It isn't covered by guardrails, and a mistake there could affect the whole Organization. The downside is a little extra setup: a separate login profile, and switching accounts when working.

## ADR-002: Host on EC2 with Docker.
We host on EC2 with Docker rather than a managed service like ECS Fargate or Amplify, because it gives full control of the server, networking and container setup, and shows I can manage the infrastructure myself (Linux, security groups, IAM roles). The downside is that I'm responsible for patching and updating the server, and for recovering it if it fails.

## ADR-003: Generate the app with Claude Code.
We generate the app with Claude Code rather than Emergent or Lovable, because the code lives in my own repo from the start, giving me full control of and access to it. Emergent was a paid subscription after a 7-day trial, and Lovable builds its backend on Supabase rather than on my AWS infrastructure. The downside is that the application code (frontend and backend) is AI-generated. I'm a cloud engineer, not a software developer, so I own and built the infrastructure around it. I still understand how the app works (ports, environment variables, database connection, health check), which is what I need to run and troubleshoot it.

## ADR-004: Build a clinic referral tracker with data governance designed in.
We build a referral tracker for a community clinic, because health and public-sector organisations rely on keeping patient records with strong data governance, and that's a realistic, in-demand problem to design for. Because it handles health-related records, governance is built in from the start: synthetic data only (no real patient details), data stored in the UK (eu-west-2 London), encryption at rest and in transit, and no patient details written to logs. The downside is that synthetic data can't prove how the system would cope with real-world volumes or a formal compliance audit (UK GDPR, NHS DSPT).

**Why no patient data in logs:** Patient data is like a password: it must never leak into logs, because logs are read by more people than the database (support staff, developers, monitoring tools), they're often copied to other systems, and they're kept for a long time with weaker protection.

## ADR-005: Keep the project in the WSL Linux home directory.
We keep the project in the WSL Linux home directory rather than on the Windows drive (/mnt/d), because it keeps the project isolated from Windows and avoids cross-system conflicts: slow file access, script permissions that don't stick (chmod +x), and Windows line endings (CRLF) breaking Bash scripts. The downside is that the files are less convenient to reach from Windows and live inside the WSL virtual disk. I work around that with explorer.exe . / code ., and by pushing to GitHub regularly so nothing exists only locally.
