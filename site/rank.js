// Ranking only: no DOM, so it can be tested in Node.

/**
 * Jobs in scope, each weighted so that large employers do not dominate.
 * A null role or country means any; remote limits the scope to remote jobs.
 */
export function jobsFor(data, { role = null, country = null, remote = false } = {}) {
  const jobs = [];
  const sizes = new Map();
  data.jobSkills.forEach((skills, i) => {
    if (role !== null && data.jobRole[i] !== role) return;
    if (country !== null && !data.jobCountries[i].includes(country)) return;
    if (remote && !data.jobRemote[i]) return;
    const company = data.jobCompany[i];
    sizes.set(company, (sizes.get(company) ?? 0) + 1);
    jobs.push({ company, role: data.jobRole[i], skills });
  });
  for (const job of jobs) job.weight = 1 / Math.sqrt(sizes.get(job.company));
  return jobs;
}

const shared = (job, owned) => job.skills.filter((s) => owned.has(s)).length;

/**
 * Per skill: demand, priority and the number of employers asking.
 * Priority is the mean of demand across all jobs and demand across jobs that use
 * the owned skills. Jobs count by how much of the smaller skill set is shared.
 */
export function rankSkills(jobs, owned) {
  const stats = new Map();
  let total = 0;
  let nearTotal = 0;
  for (const job of jobs) {
    const smaller = Math.min(job.skills.length, owned.size);
    const near = smaller ? (job.weight * shared(job, owned)) / smaller : 0;
    total += job.weight;
    nearTotal += near;
    for (const skill of job.skills) {
      let stat = stats.get(skill);
      if (!stat) stats.set(skill, (stat = { skill, all: 0, near: 0, companies: new Set() }));
      stat.all += job.weight;
      stat.near += near;
      stat.companies.add(job.company);
    }
  }
  return [...stats.values()]
    .map((s) => {
      const demand = s.all / total;
      const priority = nearTotal ? (demand + s.near / nearTotal) / 2 : demand;
      return { skill: s.skill, demand, priority, employers: s.companies.size };
    })
    .sort((a, b) => b.priority - a.priority);
}

/** Average share of a job's skills that are owned, over jobs that list any. */
export function match(jobs, owned) {
  let sum = 0;
  let total = 0;
  for (const job of jobs) {
    if (!job.skills.length) continue;
    sum += (job.weight * shared(job, owned)) / job.skills.length;
    total += job.weight;
  }
  return total ? sum / total : 0;
}

/** Roles in which a skill is most demanded, skipping roles with too few jobs in scope. */
export function rolesFor(data, scope, skill, roles, minJobs, limit) {
  return roles
    .map((role) => {
      const jobs = jobsFor(data, { ...scope, role });
      if (jobs.length < minJobs) return { role, demand: 0 };
      const total = jobs.reduce((sum, job) => sum + job.weight, 0);
      const asking = jobs.reduce((sum, job) => sum + (job.skills.includes(skill) ? job.weight : 0), 0);
      return { role, demand: total ? asking / total : 0 };
    })
    .filter((r) => r.demand > 0)
    .sort((a, b) => b.demand - a.demand)
    .slice(0, limit);
}

/** Skills most over-represented beside this one, ignoring rare pairs. */
export function pairedWith(jobs, skill, limit) {
  const inScope = new Map(rankSkills(jobs, new Set()).map((s) => [s.skill, s.demand]));
  const beside = jobs.filter((job) => job.skills.includes(skill));
  return rankSkills(beside, new Set())
    .filter((s) => s.skill !== skill && s.demand >= 0.1)
    .map((s) => ({ ...s, lift: s.demand / inScope.get(s.skill) }))
    .sort((a, b) => b.lift - a.lift)
    .slice(0, limit);
}
