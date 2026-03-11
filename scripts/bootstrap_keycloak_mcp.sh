#!/usr/bin/env sh
set -eu

KC="/opt/keycloak/bin/kcadm.sh"
REALM="mcp-platform"
GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"

$KC config credentials --server http://localhost:8080 --realm master --user admin --password admin123 >/dev/null

if ! $KC get "realms/$REALM" >/dev/null 2>&1; then
  $KC create realms -s realm="$REALM" -s enabled=true -s sslRequired=NONE >/dev/null
fi

frontend_id="$($KC get clients -r "$REALM" -q clientId=mcp-frontend --fields id --format csv --noquotes 2>/dev/null | tail -n 1 || true)"
if [ -n "$frontend_id" ]; then
  $KC update "clients/$frontend_id" -r "$REALM" \
    -s clientId=mcp-frontend \
    -s enabled=true \
    -s publicClient=true \
    -s protocol=openid-connect \
    -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=false \
    -s serviceAccountsEnabled=false \
    -s 'redirectUris=["http://localhost:3000/*"]' \
    -s 'webOrigins=["http://localhost:3000"]' >/dev/null
else
  $KC create clients -r "$REALM" \
    -s clientId=mcp-frontend \
    -s enabled=true \
    -s publicClient=true \
    -s protocol=openid-connect \
    -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=false \
    -s serviceAccountsEnabled=false \
    -s 'redirectUris=["http://localhost:3000/*"]' \
    -s 'webOrigins=["http://localhost:3000"]' >/dev/null
fi

mcp_id="$($KC get clients -r "$REALM" -q clientId=mcp-clients --fields id --format csv --noquotes 2>/dev/null | tail -n 1 || true)"
if [ -z "$mcp_id" ]; then
  $KC create clients -r "$REALM" \
    -s clientId=mcp-clients \
    -s enabled=true \
    -s publicClient=true \
    -s protocol=openid-connect \
    -s standardFlowEnabled=true >/dev/null
  mcp_id="$($KC get clients -r "$REALM" -q clientId=mcp-clients --fields id --format csv --noquotes 2>/dev/null | tail -n 1 || true)"
fi

tmp_json="/opt/keycloak/data/mcp_client_update.json"
cat >"$tmp_json" <<'EOF'
{
  "clientId": "mcp-clients",
  "enabled": true,
  "publicClient": true,
  "protocol": "openid-connect",
  "standardFlowEnabled": true,
  "directAccessGrantsEnabled": false,
  "serviceAccountsEnabled": false,
  "redirectUris": [
    "http://127.0.0.1/*",
    "http://localhost/*"
  ],
  "webOrigins": [
    "*"
  ],
  "attributes": {
    "pkce.code.challenge.method": "S256"
  }
}
EOF
$KC update "clients/$mcp_id" -r "$REALM" -f "$tmp_json" >/dev/null

google_idp_exists="$($KC get identity-provider/instances -r "$REALM" --fields alias --format csv --noquotes 2>/dev/null | grep -x google || true)"
if [ -n "$google_idp_exists" ]; then
  $KC update identity-provider/instances/google -r "$REALM" \
    -s alias=google \
    -s providerId=google \
    -s enabled=true \
    -s trustEmail=true \
    -s firstBrokerLoginFlowAlias="first broker login" \
    -s "config.clientId=$GOOGLE_CLIENT_ID" \
    -s "config.clientSecret=$GOOGLE_CLIENT_SECRET" >/dev/null
else
  $KC create identity-provider/instances -r "$REALM" \
    -s alias=google \
    -s providerId=google \
    -s enabled=true \
    -s trustEmail=true \
    -s firstBrokerLoginFlowAlias="first broker login" \
    -s "config.clientId=$GOOGLE_CLIENT_ID" \
    -s "config.clientSecret=$GOOGLE_CLIENT_SECRET" >/dev/null
fi

$KC update "realms/$REALM" -s sslRequired=NONE >/dev/null
echo "READY"
