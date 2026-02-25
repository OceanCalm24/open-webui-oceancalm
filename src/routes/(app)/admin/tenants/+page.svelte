<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { getTenants, createTenant, updateTenant, getAgencyUsers, addAgencyUser, removeAgencyUser } from '$lib/apis/tenants';
	import type { Tenant, TenantUser } from '$lib/apis/tenants';

	let tenants: Tenant[] = [];
	let agencyUsers: TenantUser[] = [];
	let loading = true;
	let showCreateForm = false;
	let showAddAgency = false;
	let newName = '';
	let newSlug = '';
	let newAgencyEmail = '';
	let error = '';

	onMount(async () => {
		if (!$user?.is_super_admin) {
			goto('/');
			return;
		}
		await loadTenants();
	});

	async function loadTenants() {
		try {
			[tenants, agencyUsers] = await Promise.all([
				getTenants(localStorage.token),
				getAgencyUsers(localStorage.token)
			]);
		} catch (e) {
			error = 'Failed to load data';
		} finally {
			loading = false;
		}
	}

	async function handleAddAgencyUser() {
		if (!newAgencyEmail) return;
		try {
			await addAgencyUser(localStorage.token, newAgencyEmail);
			newAgencyEmail = '';
			showAddAgency = false;
			await loadTenants();
		} catch (e: any) {
			error = e?.detail || 'Failed to add agency user';
		}
	}

	async function handleRemoveAgencyUser(userId: string) {
		try {
			await removeAgencyUser(localStorage.token, userId);
			await loadTenants();
		} catch (e: any) {
			error = e?.detail || 'Failed to remove agency user';
		}
	}

	async function handleCreate() {
		if (!newName || !newSlug) return;
		try {
			await createTenant(localStorage.token, { name: newName, slug: newSlug });
			newName = '';
			newSlug = '';
			showCreateForm = false;
			await loadTenants();
		} catch (e) {
			error = 'Failed to create tenant';
		}
	}

	async function toggleActive(tenant: Tenant) {
		try {
			await updateTenant(localStorage.token, tenant.id, {
				is_active: !tenant.is_active
			});
			await loadTenants();
		} catch (e) {
			error = 'Failed to update tenant';
		}
	}

	function slugify(name: string) {
		return name
			.toLowerCase()
			.replace(/\s+/g, '-')
			.replace(/[^a-z0-9-]/g, '');
	}
</script>

<div class="p-6 max-w-5xl mx-auto">
	<div class="flex items-center justify-between mb-6">
		<h1 class="text-2xl font-bold">Tenants</h1>
		<button
			class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
			on:click={() => (showCreateForm = !showCreateForm)}
		>
			+ New Tenant
		</button>
	</div>

	{#if error}
		<div class="mb-4 p-3 bg-red-100 text-red-700 rounded">{error}</div>
	{/if}

	{#if showCreateForm}
		<div class="mb-6 p-4 border rounded bg-gray-50 dark:bg-gray-800">
			<h2 class="font-semibold mb-3">Create Tenant</h2>
			<div class="flex gap-3 flex-wrap">
				<input
					bind:value={newName}
					on:input={() => (newSlug = slugify(newName))}
					placeholder="Tenant name"
					class="border rounded px-3 py-2 flex-1"
				/>
				<input
					bind:value={newSlug}
					placeholder="slug (auto-filled)"
					class="border rounded px-3 py-2 flex-1"
				/>
				<button
					class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
					on:click={handleCreate}
				>
					Create
				</button>
			</div>
		</div>
	{/if}
</div>

<!-- Agency Team Section -->
<div class="p-6 max-w-5xl mx-auto mt-2">
	<div class="flex items-center justify-between mb-3">
		<h2 class="text-lg font-semibold">Agency Team <span class="text-sm font-normal text-gray-500">(Super Admins)</span></h2>
		<button
			class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
			on:click={() => (showAddAgency = !showAddAgency)}
		>
			+ Add Member
		</button>
	</div>

	{#if showAddAgency}
		<div class="mb-4 p-4 border rounded bg-gray-50 dark:bg-gray-800 flex gap-3">
			<input
				bind:value={newAgencyEmail}
				placeholder="Email of existing user to promote"
				type="email"
				class="border rounded px-3 py-2 flex-1"
			/>
			<button
				class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
				on:click={handleAddAgencyUser}
			>
				Promote to Super Admin
			</button>
		</div>
	{/if}

	<table class="w-full border-collapse">
		<thead>
			<tr class="border-b text-left text-sm text-gray-500">
				<th class="py-2 pr-4">Name</th>
				<th class="py-2 pr-4">Email</th>
				<th class="py-2">Actions</th>
			</tr>
		</thead>
		<tbody>
			{#each agencyUsers as member}
				<tr class="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
					<td class="py-3 pr-4 font-medium">{member.name}</td>
					<td class="py-3 pr-4 text-gray-500 text-sm">{member.email}</td>
					<td class="py-3">
						{#if member.id !== $user?.id}
							<button
								class="text-sm text-red-500 hover:underline"
								on:click={() => handleRemoveAgencyUser(member.id)}
							>
								Remove
							</button>
						{:else}
							<span class="text-xs text-gray-400">You</span>
						{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<div class="p-6 max-w-5xl mx-auto border-t border-gray-200 dark:border-gray-700 pt-6">
	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if tenants.length === 0}
		<p class="text-gray-500">No tenants yet. Create your first one above.</p>
	{:else}
		<table class="w-full border-collapse">
			<thead>
				<tr class="border-b text-left text-sm text-gray-500">
					<th class="py-2 pr-4">Name</th>
					<th class="py-2 pr-4">Slug</th>
					<th class="py-2 pr-4">Status</th>
					<th class="py-2 pr-4">Created</th>
					<th class="py-2">Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each tenants as tenant}
					<tr class="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
						<td class="py-3 pr-4 font-medium">{tenant.name}</td>
						<td class="py-3 pr-4 text-gray-500 text-sm">{tenant.slug}</td>
						<td class="py-3 pr-4">
							<span
								class="px-2 py-1 text-xs rounded-full {tenant.is_active
									? 'bg-green-100 text-green-700'
									: 'bg-gray-100 text-gray-500'}"
							>
								{tenant.is_active ? 'Active' : 'Inactive'}
							</span>
						</td>
						<td class="py-3 pr-4 text-sm text-gray-500">
							{new Date(tenant.created_at * 1000).toLocaleDateString()}
						</td>
						<td class="py-3 flex gap-2">
							<a
								href="/admin/tenants/{tenant.id}"
								class="text-sm text-blue-600 hover:underline"
							>
								Manage
							</a>
							<button
								class="text-sm text-gray-500 hover:underline"
								on:click={() => toggleActive(tenant)}
							>
								{tenant.is_active ? 'Deactivate' : 'Activate'}
							</button>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>
