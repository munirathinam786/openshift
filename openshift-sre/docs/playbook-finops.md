# FinOps & Optimization Playbook

This playbook covers spend visibility, chargeback drilldowns, forecast review, commitment coverage, and cost optimization recommendations.

## Cost and usage summary

Use: `list_cost_and_usage_summary`

What to look for:

- sharp spend changes across the selected window
- daily spikes that do not align with expected releases or experiments
- monthly totals that outpace the current operating plan

Suggested prompts:

- `Summarize cluster resource utilization over the last 30 days and call out any obvious spikes.`

## Cost by service

Use: `list_cost_by_service`

What to look for:

- top services dominating spend unexpectedly
- recent growth in services that should be flat or seasonal
- storage, analytics, or data-transfer services growing faster than expected

Suggested prompts:

- `Break down cost by service for the last 30 days and highlight the top cost drivers.`

## Cost by tag

Use: `list_cost_by_tag`

What to look for:

- missing ownership or environment allocation
- large `<unallocated>` or blank tag spend
- teams or workloads with sudden spend drift

Suggested prompts:

- `Break down cost by tag for Environment and call out unallocated spend.`
- `Summarize spend by Owner tag and identify the biggest cost concentrations.`

## Cost forecast

Use: `get_cost_forecast`

What to look for:

- next-month forecast exceeding current run-rate expectations
- prediction intervals wide enough to suggest unstable usage patterns
- forecast drift that should trigger a planning review

Suggested prompts:

- `Forecast the next month of spend and explain whether the range looks risky.`

## Savings Plans coverage

Use: `list_savings_plans_coverage`

What to look for:

- low average coverage despite stable compute usage
- rising on-demand share in what should be committed workloads
- coverage gaps that align with newly deployed fleets or regions

Suggested prompts:

- `Review Savings Plans coverage and explain where on-demand spend still dominates.`

## Rightsizing recommendations

Use: `list_rightsizing_recommendations`

What to look for:

- large estimated monthly savings concentrated in a small number of instances
- repeated same-family downsizing opportunities
- cost optimization opportunities that need coordination with platform owners

Suggested prompts:

- `Review EC2 rightsizing recommendations and summarize the top savings opportunities.`

## Recommended FinOps drilldown workflow

1. start with `list_cost_and_usage_summary` to establish the current run rate
2. use `list_cost_by_service` to identify the top cost concentrations
3. use `list_cost_by_tag` to attribute spend to teams or environments
4. use `get_cost_forecast` to understand forward risk
5. use `list_savings_plans_coverage` to inspect commitment posture
6. use `list_rightsizing_recommendations` to turn findings into optimization actions

## Recommendation patterns the agent should surface

- reduce or remove unallocated tag spend by enforcing cost-allocation tags
- review top-service growth before the next billing cycle closes
- improve Savings Plans coverage for stable compute-heavy workloads
- validate rightsizing recommendations with application owners before execution
- pair forecast growth with deployment calendars, data retention changes, or scaling events
