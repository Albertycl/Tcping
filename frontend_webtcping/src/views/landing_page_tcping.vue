<template>
  <div>
    <landing_page_tcping></landing_page_tcping>
  </div>
</template>

<script>
// @ is an alias to /src
import landing_page_tcping from "@/components/landing_page/tcping/landing_page_tcping.vue";

export default {
  name: "Home",
  components: {
    landing_page_tcping,
  },
};
</script>
