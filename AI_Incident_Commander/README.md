\# AI Production Incident Commander



An AI-assisted production incident management and automated remediation platform built using Python, FastAPI, Prometheus, Grafana, Docker, and Streamlit.



\## Project Overview



AI Production Incident Commander is designed to monitor applications, detect failures, investigate incidents, recommend solutions, and automatically recover applications after human approval.



It demonstrates how production monitoring and incident response can be automated.



\## Key Features



\- Real-time application health monitoring

\- Prometheus metrics collection

\- Grafana alert generation

\- Automated incident creation using webhooks

\- AI-assisted incident investigation using TF-IDF and runbooks

\- Human-approved remediation

\- Automated database recovery

\- Post-remediation health verification

\- Incident and execution report generation

\- Interactive Streamlit dashboard

\- Docker-based deployment



\## Technology Stack



| Technology | Purpose |

|---|---|

| Python | Core programming language |

| FastAPI | Backend API development |

| Prometheus | Application metrics monitoring |

| Grafana | Monitoring and alerting |

| Loki | Application log collection |

| SQLite | Incident and remediation storage |

| TF-IDF | Runbook retrieval |

| Streamlit | Interactive dashboard |

| Docker | Containerization |



\## System Architecture



```text

Sample Messaging Application

&#x20;          |

&#x20;      Prometheus

&#x20;          |

&#x20;        Grafana

&#x20;          |

&#x20;     Alert Webhook

&#x20;          |

&#x20;  FastAPI Incident Manager

&#x20;          |

&#x20;  Incident Investigation

&#x20;          |

&#x20;   Human Approval

&#x20;          |

&#x20; Automated Remediation

&#x20;          |

&#x20;   Health Verification

&#x20;          |

&#x20;    Incident Resolved

```



\## Project Workflow



1\. The sample messaging application experiences a database failure.

2\. Prometheus detects the database availability metric changing from 1 to 0.

3\. Grafana generates an alert.

4\. FastAPI receives the alert through a webhook.

5\. The system creates an incident and stores it in SQLite.

6\. The investigation module searches relevant runbooks and recommends a remediation action.

7\. An administrator reviews and approves the action.

8\. The system executes the recovery operation.

9\. Application health is checked again.

10\. The incident is marked resolved after successful verification.



\## Project Structure



```text

AI\_Incident\_Commander/

│

├── app/

│   ├── ai\_investigator.py

│   ├── database.py

│   ├── incident\_receiver.py

│   ├── main.py

│   ├── monitoring.py

│   └── remediation.py

│

├── dashboard/

│   └── dashboard.py

│

├── data/

│

├── knowledge\_base/

│   └── runbooks/

│

├── prometheus/

│   └── prometheus.yml

│

├── sample\_application/

│   └── main.py

│

├── Dockerfile

├── docker-compose.yml

├── requirements.txt

└── README.md

```



\## Running the Project



Clone the repository:



```bash

git clone https://github.com/Imamali07/Projects.git

```



Navigate to the project:



```bash

cd Projects/AI\_Incident\_Commander

```



Start the Docker containers:



```bash

docker compose up -d --build

```



\## Application URLs



| Service | URL |

|---|---|

| Streamlit Dashboard | http://localhost:8501 |

| FastAPI Backend | http://localhost:8002 |

| Swagger API Documentation | http://localhost:8002/docs |

| Grafana | http://localhost:3000 |

| Prometheus | http://localhost:9090 |



\## Example Incident



\*\*Problem:\*\* Database connectivity failure in the messaging application.



\*\*Detection:\*\* Prometheus detects database availability as 0.



\*\*Investigation:\*\* The system searches troubleshooting runbooks and recommends checking database connectivity.



\*\*Approval:\*\* An administrator approves the remediation.



\*\*Recovery:\*\* The system executes the database recovery endpoint.



\*\*Verification:\*\* The application health check passes and the incident is marked resolved.



\## Future Enhancements



\- LLM-powered incident investigation

\- Slack and Microsoft Teams notifications

\- Kubernetes integration

\- Cloud monitoring integrations

\- Advanced incident analytics

\- Multi-application monitoring



\## Project Objective



To demonstrate an automated production incident management system that combines monitoring, AI-assisted investigation, human-approved remediation, and automated recovery verification.



\---



\*\*Developed using Python, FastAPI, Prometheus, Grafana, Streamlit, and Docker.\*\*

