# Immigration Questionnaire System (mm_questionnaire)

## Overview

Phase 2 module of the Immigration Portal system providing a two-stage questionnaire system for client data collection.

## Features

### Pre-Consultation Questionnaire (Q1)
Initial eligibility screening with 7 sections:
1. Personal Information
2. Immigration Intent
3. Education
4. Work Experience
5. Language Ability
6. Canada Connections
7. Financial & Risk Factors

### Detailed Assessment Questionnaire (Q2)
Comprehensive data collection for CRS calculation with 7 sections:
1. Principal Applicant Details
2. Spouse/Partner Details (conditional)
3. Dependent Children
4. Education Details
5. Work Experience
6. Language Proficiency
7. Settlement Funds

## Technical Features

- **Section-by-section navigation** with progress tracking
- **Auto-save on field blur/change** (Google Forms-like UX)
- **Direct profile population** (no intermediate data storage)
- **Repeater sections** for children, education, work experience, language tests
- **Conditional sections** (spouse section shown based on marital status)
- **Stage automation** (Q1 → Onboarding, Q2 → Roadmap)
- **CLB score calculation** from IELTS/CELPIP/TEF/TCF scores

## Models

| Model | Description |
|-------|-------------|
| `mm.questionnaire.response` | Tracks completion state per case |
| `mm.education.record` | Education credentials with ECA tracking |
| `mm.work.experience` | Work history with NOC/TEER classification |
| `mm.language.proficiency` | Language test scores with CLB conversion |

## Dependencies

- `mm_immigration` (Phase 1 core module)
- `mm_portal` (Phase 1 portal module)
- `website` (Odoo portal framework)

## Installation

1. Place module in Odoo addons path
2. Update app list: Settings → Apps → Update Apps List
3. Install: Search for "Immigration Questionnaire System"

## Portal Routes

| Route | Description |
|-------|-------------|
| `/my/immigration/questionnaire/pre` | Start Q1 |
| `/my/immigration/questionnaire/detailed` | Start Q2 |
| `/my/immigration/questionnaire/<type>/section/<n>` | Section page |
| `/my/immigration/questionnaire/<type>/review` | Review & submit |

## AJAX Endpoints

All endpoints use JSON-RPC format:

- `POST /my/immigration/questionnaire/save` - Save single field
- `POST /my/immigration/questionnaire/complete-section` - Mark section complete
- `POST /my/immigration/questionnaire/submit` - Submit questionnaire
- `POST /my/immigration/questionnaire/add-education` - Add education record
- `POST /my/immigration/questionnaire/add-experience` - Add work experience
- `POST /my/immigration/questionnaire/add-language` - Add language test
- `POST /my/immigration/questionnaire/add-child` - Add dependent child

## Security

- Portal users can only access their own case data
- Consultants can access assigned cases
- Managers have full access
- Record rules enforce data isolation

## Workflow Integration

```
Client Invited → Q1 Started → Q1 Complete → Onboarding Stage
                                              ↓
                                         (Payment - Phase 3)
                                              ↓
Assessment Stage → Q2 Started → Q2 Complete → Roadmap Stage
```

## Version

- Odoo: 19.0
- Module: 1.0.0

## Author

The Migration Monitor  
https://themigrationmonitor.ca

## License

LGPL-3
