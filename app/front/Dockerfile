FROM nginx:1.27-alpine

ARG APP_VERSION=1.0
ARG COULEUR=#b5651d

# BACK_URL est injecté dans la conf nginx au démarrage (templates du conteneur nginx).
ENV BACK_URL=http://back:8080

COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY index.html /usr/share/nginx/html/index.html
RUN sed -i "s|__VERSION__|${APP_VERSION}|g; s|__COULEUR__|${COULEUR}|g" /usr/share/nginx/html/index.html

EXPOSE 80
