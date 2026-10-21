<template>
  <div>
    <landing_page_curl></landing_page_curl>
  </div>
</template>

<script>
// @ is an alias to /src
import landing_page_curl from "@/components/landing_page/tcping/landing_page_curl.vue";

export default {
  name: "Home",
  components: {
    landing_page_curl,
  },
};
</script>
