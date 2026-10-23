import Keycloak from 'keycloak-js'

export const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? `${location.origin}/auth`,
  realm: 'vagacerta',
  clientId: 'vagacerta-web',
})

export async function authorization() {
  await keycloak.updateToken(30)
  return { Authorization: `Bearer ${keycloak.token}` }
}
