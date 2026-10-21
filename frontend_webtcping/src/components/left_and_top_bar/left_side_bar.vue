<template>
  <v-card>
    <v-navigation-drawer permanent expand-on-hover app>
      <v-divider></v-divider>

      <v-list nav dense>
        <v-list-item link>
          <v-list-item-title>
            <router-link to="/route_create_or_close_position"
              >TCPING_CT</router-link
            >
          </v-list-item-title>
        </v-list-item>
      
      </v-list>
    </v-navigation-drawer>
  </v-card>
</template>

<style scoped>
a {
  text-decoration: none;
}
</style>
