<script lang="ts">
  import Router from 'svelte-spa-router'
  import MainLayout from './lib/components/layout/MainLayout.svelte'

  // Lazy load routes
  import Home from './routes/Home.svelte'
  import Dashboard from './routes/Dashboard.svelte'
  import History from './routes/History.svelte'

  const routes = {
    '/': Home,
    '/dashboard': Dashboard,
    '/history': History,
  }
</script>

<MainLayout>
  <Router {routes} on:conditionsFailed on:routeLoaded />
</MainLayout>
