<template>
  <div>
    <landing_page_tcp_trace></landing_page_tcp_trace>
  </div>
</template>

<script>
// @ is an alias to /src
import landing_page_tcp_trace from "@/components/landing_page/tcping/landing_page_tcp_trace.vue";

export default {
  name: "Home",
  components: {
    landing_page_tcp_trace,
  },
};
</script>
