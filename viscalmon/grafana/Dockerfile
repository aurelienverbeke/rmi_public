FROM grafana/grafana:13.1.0

COPY datasources.yaml /etc/grafana/provisioning/datasources/datasources.yaml
COPY dashboards.yaml /etc/grafana/provisioning/dashboards/dashboards.yaml
COPY dashboards /etc/grafana/dashboards/

ENV GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/etc/grafana/dashboards/home.json
ENV GF_AUTH_ANONYMOUS_ENABLED=true
ENV GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
ENV GF_AUTH_ANONYMOUS_HIDE_VERSION=false

#RUN grafana-cli plugins install volkovlabs-image-panel
#RUN grafana-cli plugins install marcusolsson-static-datasource 1.4.3