<template>
  <div>
    <landing_page_http_ping></landing_page_http_ping>
  </div>
</template>

<script>
// @ is an alias to /src
import landing_page_http_ping from "@/components/landing_page/tcping/landing_page_http_ping.vue";

export default {
  name: "Home",
  components: {
    landing_page_http_ping,
  },
};
</script>
