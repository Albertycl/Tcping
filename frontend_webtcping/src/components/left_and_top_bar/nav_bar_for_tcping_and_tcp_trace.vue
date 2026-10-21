<template>
  <div>
    <v-app-bar color="blue darken-2" dense dark>
      <!-- <v-app-bar-nav-icon></v-app-bar-nav-icon> -->

      <!-- <v-toolbar-title>Page title</v-toolbar-title> -->

      <v-spacer></v-spacer>

      <!-- <v-btn icon>
        <v-icon>mdi-heart</v-icon>
      </v-btn>

      <v-btn icon>
        <v-icon>mdi-magnify</v-icon>
      </v-btn> -->
      <v-btn text :class="{ 'nav-active': $route.path === '/' }">
        <router-link to="/" class="mt-4 white--text">TCPING </router-link>
      </v-btn>
       <v-btn text :class="{ 'nav-active': $route.path === '/httping' }">
        <router-link to="/httping" class="mt-4 white--text">HTTP-PING </router-link>
      </v-btn>
      <v-btn text :class="{ 'nav-active': $route.path === '/tcp_trace' }">
        <router-link to="/tcp_trace" class="mt-4 white--text"
          >TCP_TRACE
        </router-link>
      </v-btn>
      <v-btn text :class="{ 'nav-active': $route.path === '/dig' }">
        <router-link to="/dig" class="mt-4 white--text">DIG </router-link>
      </v-btn>
      <v-btn text :class="{ 'nav-active': $route.path === '/curl' }">
        <router-link to="/curl" class="mt-4 white--text">CURL </router-link>
      </v-btn>
      <v-btn text :class="{ 'nav-active': $route.path === '/customized' }">
        <router-link to="/customized" class="mt-4 white--text">CUSTOMIZED </router-link>
      </v-btn>
      <v-btn text :class="{ 'nav-active': $route.path === '/all-in-one' }">
        <router-link to="/all-in-one" class="mt-4 white--text">ALL-IN-ONE </router-link>
      </v-btn>
    </v-app-bar>
  </div>
</template>

<style scoped>
a {
  text-decoration: none;
}

.nav-active {
  background-color: rgba(255, 255, 255, 0.2) !important;
  border-bottom: 3px solid white;
}
</style>
