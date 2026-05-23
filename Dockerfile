FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html.template
CMD ["/bin/sh", "-c", "sed -i 's/listen \\(.*\\)80;/listen \\1'\"$PORT\"';/g' /etc/nginx/conf.d/default.conf && envsubst '${BACKEND_URL}' < /usr/share/nginx/html/index.html.template > /usr/share/nginx/html/index.html && nginx -g 'daemon off;'"]
EXPOSE 80
