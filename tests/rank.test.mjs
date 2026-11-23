import assert from "node:assert/strict";
import { test } from "node:test";
import { jobsFor, match, pairedWith, rankSkills, rolesFor } from "../site/rank.js";

// Skills: 0 and 1 belong together, 2 stands alone and is the most common.
const data = {
  jobCompany: [0, 1, 2, 3, 4],
  jobRole: [0, 0, 0, 1, 1],
  jobSkills: [[0, 1], [0, 1], [2], [2], [2]],
};

test("with no skills, priority equals demand", () => {
  const ranked = rankSkills(jobsFor(data, null), new Set());
  assert.equal(ranked[0].skill, 2);
  for (const s of ranked) assert.ok(Math.abs(s.priority - s.demand) < 1e-9);
});

test("owning a skill lifts the skills listed beside it", () => {
  const ranked = rankSkills(jobsFor(data, null), new Set([0]));
  assert.equal(ranked.find((s) => s.skill !== 0).skill, 1);
});

test("a large employer is damped", () => {
  const jobs = jobsFor({ jobCompany: [0, 0, 0, 0, 1], jobRole: [0, 0, 0, 0, 0], jobSkills: [[0], [0], [0], [0], [1]] }, 0);
  const share = rankSkills(jobs, new Set()).find((s) => s.skill === 0).demand;
  assert.ok(Math.abs(share - 2 / 3) < 1e-9);
});

test("match averages the share of skills owned", () => {
  assert.equal(match(jobsFor(data, 0), new Set([0])), (0.5 + 0.5 + 0) / 3);
  assert.equal(match([], new Set([0])), 0);
});

test("roles and pairs", () => {
  assert.deepEqual(rolesFor(data, 2, [0, 1], 5).map((r) => r.role), [1, 0]);
  assert.deepEqual(pairedWith(jobsFor(data, null), 0, 5).map((s) => s.skill), [1]);
});

test("owned skills that no job uses leave priority equal to demand", () => {
  for (const s of rankSkills(jobsFor(data, null), new Set([9]))) assert.equal(s.priority, s.demand);
});
