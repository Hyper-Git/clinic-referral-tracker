# Clinic Referral Tracker

A cloud platform for a small community clinic's referral tracker: secure, monitored, recoverable and deployed through code, for under $20 a month.

> 🚧 Work in progress. See the progress checklist below.

## The problem
A small community clinic receives referrals from GP practices and tracks them in spreadsheets and email. Urgent referrals get buried, nobody can quickly see how long patients have been waiting, and there's no record of who changed what. Because these are health-related records, the system must be built with data governance in mind.

## What the app does
- Log a referral (synthetic reference, referring practice, priority, date received)
- Track its status: received → triaged → booked → seen
- Show a board sorted by priority and days waiting, flagging long waits

## What I built (the platform)
| Need | Solution |
|---|---|
| Available during clinic hours | EC2 behind a load balancer with health checks |
| Patient data protected | Private subnets, tight security groups, least-privilege IAM, encryption, UK region |
| Problems spotted early | CloudWatch logs, alarms and email alerts |
| Data recoverable | Nightly database backups to S3, restore tested |
| Safe, repeatable changes | Terraform + GitHub Actions CI/CD |
| Affordable | Small instance, budget alerts, tear down when idle |

## Tech stack
AWS (EC2, VPC, ALB, IAM, S3, CloudWatch) · Terraform · Docker · GitHub Actions · Bash · Python · PostgreSQL

## Data governance
Synthetic data only, never real patient details. Data stays in the UK (eu-west-2). Encrypted at rest and in transit. No patient details in logs.

## Ownership
The infrastructure, pipeline, scripts and documentation are my own work. The application code was generated with Claude Code. I'm a cloud engineer, not a software developer. See [ADR-003](docs/decisions.md).

## Progress
- [ ] Phase 0: Repo, budget alerts, decision records
- [ ] Phase 1: App running in Docker locally
- [ ] Phase 2: Terraform: VPC, networking, security, remote state
- [ ] Phase 3: EC2, IAM, load balancer, app live
- [ ] Phase 4: Bash deploy and backup scripts
- [ ] Phase 5: Monitoring and alerting
- [ ] Phase 6: CI/CD with GitHub Actions
- [ ] Phase 7: Python health-check script
- [ ] Phase 8: Azure equivalents
- [ ] Phase 9: Final walkthrough

## Documentation
- [Decisions (ADRs)](docs/decisions.md)
- [Troubleshooting log](docs/troubleshooting.md)

## Licence
MIT