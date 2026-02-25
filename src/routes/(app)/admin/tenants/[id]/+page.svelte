<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { getTenantUsers, addTenantUser } from '$lib/apis/tenants';

	let tenantId = $page.params.id;
	let users: any[] = [];
	let loading = true;
	let showAddUser = false;
	let newEmail = '';
	let newName = '';
	let newPassword = '';
	let newRole = 'user';
	let error = '';

	onMount(async () => {
		if (!$user?.is_super_admin) {
			goto('/');
			return;
		}
		await loadUsers();
	});

	async function loadUsers() {
		try {
			users = await getTenantUsers(localStorage.token, tenantId);
		} catch (e) {
			error = 'Failed to load users';
		} finally {
			loading = false;
		}
	}

	async function handleAddUser() {
		if (!newEmail || !newName || !newPassword) return;
		try {
			await addTenantUser(localStorage.token, tenantId, {
				email: newEmail,
				name: newName,
				password: newPassword,
				role: newRole
			});
			newEmail = '';
			newName = '';
			newPassword = '';
			showAddUser = false;
			await loadUsers();
		} catch (e) {
			error = 'Failed to add user';
		}
	}
</script>

<div class="p-6 max-w-4xl mx-auto">
	<a href="/admin/tenants" class="text-sm text-gray-500 hover:underline mb-4 block">
		← Back to Tenants
	</a>

	<div class="flex items-center justify-between mb-6">
		<h1 class="text-2xl font-bold">Tenant Users</h1>
		<button
			class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
			on:click={() => (showAddUser = !showAddUser)}
		>
			+ Add User
		</button>
	</div>

	{#if error}
		<div class="mb-4 p-3 bg-red-100 text-red-700 rounded">{error}</div>
	{/if}

	{#if showAddUser}
		<div class="mb-6 p-4 border rounded bg-gray-50 dark:bg-gray-800 space-y-3">
			<h2 class="font-semibold">Add User to Tenant</h2>
			<div class="grid grid-cols-2 gap-3">
				<input bind:value={newName} placeholder="Full name" class="border rounded px-3 py-2" />
				<input
					bind:value={newEmail}
					placeholder="Email"
					type="email"
					class="border rounded px-3 py-2"
				/>
				<input
					bind:value={newPassword}
					placeholder="Password"
					type="password"
					class="border rounded px-3 py-2"
				/>
				<select bind:value={newRole} class="border rounded px-3 py-2">
					<option value="user">User</option>
					<option value="admin">Admin</option>
				</select>
			</div>
			<button
				class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
				on:click={handleAddUser}
			>
				Add User
			</button>
		</div>
	{/if}

	{#if loading}
		<p class="text-gray-500">Loading users...</p>
	{:else if users.length === 0}
		<p class="text-gray-500">No users in this tenant yet.</p>
	{:else}
		<table class="w-full border-collapse">
			<thead>
				<tr class="border-b text-left text-sm text-gray-500">
					<th class="py-2 pr-4">Name</th>
					<th class="py-2 pr-4">Email</th>
					<th class="py-2">Role</th>
				</tr>
			</thead>
			<tbody>
				{#each users as u}
					<tr class="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
						<td class="py-3 pr-4">{u.name}</td>
						<td class="py-3 pr-4 text-gray-500">{u.email}</td>
						<td class="py-3">
							<span class="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600"
								>{u.role}</span
							>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>
