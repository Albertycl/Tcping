<template>
  <div>
    <nav_bar_for_tcping_and_tcp_trace></nav_bar_for_tcping_and_tcp_trace>
    <v-container fluid>
      <whitelist_management></whitelist_management>
    </v-container>
  </div>
</template>

<script>
import nav_bar_for_tcping_and_tcp_trace from "@/components/left_and_top_bar/nav_bar_for_tcping_and_tcp_trace.vue";
import WhitelistManagement from "@/components/components_within_the_page/WhitelistManagement.vue";

export default {
  components: {
    nav_bar_for_tcping_and_tcp_trace,
    whitelist_management: WhitelistManagement,
  },
};
</script>
