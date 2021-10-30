from typing import *
import json
import argparse
import subprocess

class gh:
    def branch_list(path) -> List[str]:
        res = []
        ret = subprocess.run(['git', '--no-pager', '-C', path, 'branch', 'list', '--all', '--no-color'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True)

        if ret.returncode == 0:
            for l in ret.stdout.splitlines():
                if len(l.strip()) > 0:
                    res.append(l[2:])
        else:
            print("error:", ret)
        return res


    def common_ancestor(path, branch1, branch2) -> str:
        ret = subprocess.run(['git', '--no-pager', '-C', path, 'merge-base', branch1, branch2],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True)
        if ret.returncode == 0:
            id = ret.stdout.strip()
            # print("     id="+id)
            return id
        else:
            print("error:", ret)
        return None


    def count_commits(path, branch1, branch2) -> int:
        ret = subprocess.run(['git', '--no-pager', '-C', path, 'rev-list', "--count", branch1+".."+branch2],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True)
        if ret.returncode == 0:
            return int(ret.stdout.strip())
        else:
            print("error:", ret)
        return 0


    def log_range(path, branch1, branch2) -> List[Tuple[str, str, str]]:
        res = []
        ret = subprocess.run(['git', '--no-pager', '-C', path, 'log', branch1+'..'+branch2, '--pretty=format:%H|%ci|%s'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True)
        if ret.returncode == 0:
            for l in ret.stdout.strip().splitlines():
                split = l.split('|')
                id = split[0]
                commit_date = split[1]
                msg = ''

                if len(split) > 2:
                    msg = split[2]

                res.append(id, commit_date, msg)
        else:
            print("error:", ret)
        return res


    def log_single(path: str, commitId: str) -> Tuple[str, str, str]:
        ret = subprocess.run(['git', '--no-pager', '-C', path, 'log', commitId, '-1', '--pretty=format:%H|%ci|%s'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True)
        if ret.returncode == 0:
            split = ret.stdout.strip().split('|')
            id = split[0]
            commit_date = split[1]
            msg = ''
            if len(split) > 2:
                msg = split[2]
            # print("     id="+id+" date="+commit_date)
            return (id, commit_date, msg)
        else:
            print("error:", ret)
        return (None, None, '')


    def is_ancestor(path, commit1, commit2) -> bool:
        ret = subprocess.run(['git', '--no-pager', '-C', path, 'merge-base', '--is-ancestor', commit1, commit2],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True)
        # if ret.returncode == 0:
        #     msg = "true"
        # print("     result="+msg+","+commit1+","+commit2)
        if ret.returncode == 0:
            return True
        else:
            return False


class NodeContainer:
    def __init__(self, id, inner_node, date_str):
        self.id = id
        self.date = date_str
        self.inner_node = inner_node


class GitTree:
    def __init__(self):
        self.home = None
        self.id_to_branch: Dict[str, List[str]] = {}
        self.git_node_ids: Dict[str, int] = {}
        self.git_nodes: List[NodeContainer] = []
        self.branch_point_to_date = {}

        self.commit_count = None
        self.ancestors = None
        self.adjancency = None

        self.branches = None

    def init(self, home: str, branches: List[str]):
        self.home: str = home
        self.branches = branches
        size = len(branches)*2
        self.commit_count: List[List[int]] = [[0 for i in range(size)] for j in range(size)]
        self.ancestors: List[List[bool]] = [[False for i in range(size)] for j in range(size)]
        return self

    def get_branch_point_date(self, id):
        result = self.branch_point_to_date.get(id)
        if result == None:
            result = gh.log_single(self.home, id)[1]
            self.branch_point_to_date[id] = result

        return result

    def id_from_git_node(self, node: str, inner: bool) -> int:
        id = self.git_node_ids.get(node)
        if id==None:
            id = len(self.git_nodes)
            # print("GGX id:{}".format(id))
            self.git_node_ids[node] = id
            dstr = self.get_branch_point_date(node)
            self.git_nodes.append(NodeContainer(node, inner, dstr))

        return id

    def find_ids(self, branches: List[str]) -> List[str]:
        for branch in branches:
            id = gh.log_single(self.home, branch)[0]
            lst = self.id_to_branch.get(id)
            if lst == None:
                lst = []
                self.id_to_branch[id] = lst
            lst.append(branch)

        return sorted(list(self.id_to_branch))

    def add_ancestor_node(self, b1, b2, an_node):
        b1_id = self.id_from_git_node(b1, False)
        b2_id = self.id_from_git_node(b2, False)
        anc_id = self.id_from_git_node(an_node, True)
        print(str(b1_id)+";" + str(b2_id)+";"+str(anc_id))
        if b1_id == anc_id:
            # print("B0:"+str(b2_id)+","+str(anc_id));
            self.ancestors[anc_id][b2_id] = True
        elif b2_id == anc_id:
            # print("B1:"+str(b1_id)+","+str(anc_id))
            self.ancestors[anc_id][b1_id] = True
        else:
            # print("A0:{} {}".format(
            #      len(self.ancestors), len(self.ancestors[0])))
            # print("AA:{} {} {} {}".format(anc_id, b1_id, b2_id, an_node))
            self.ancestors[anc_id][b1_id] = True
            self.ancestors[anc_id][b2_id] = True
        # print("MMMM={}".format(self.ancestors[0][1]))

    def add_common_ancestors(self, branches: List[str]):
        size = len(branches)
        for i in range(size):
            for j in range(i+1, size):
                b1 = branches[i]
                b2 = branches[j]
                anc_node = gh.common_ancestor(self.home, b1, b2)
                if anc_node != None:
                    # print("    COMMON: "+b1+","+b2)
                    self.add_ancestor_node(b1, b2, anc_node)

    def fill_graph(self):
        size = len(self.git_nodes)
        print("size:=",size)
        for i in range(size):
            for j in range(size):
                if i == j:
                    continue
                
                if self.ancestors[i][j]==False:
                    self.ancestors[i][j] = gh.is_ancestor(
                        self.home, self.git_nodes[i].id, self.git_nodes[j].id)
                    print("  ancestor:{},{}:{}".format(i,j,self.ancestors[i][j]))

        print("ancestor_to_adjancency...")
        self.adjancency = GitTree.ancestor_matrix_to_adjacency_matrix(
            self.ancestors)

        # for i in range(size):
        #     for j in range(size):
        #         print("AJ:",i,j,self.adjancency[i][j])

        for i in range(size):
            for j in range(size):
                if self.adjancency[i][j]:
                    self.commit_count[i][j] = gh.count_commits(
                        self.home, self.git_nodes[i].id, self.git_nodes[j].id)
                    print("  commit_count:{},{}:{}".format(i,j,self.commit_count[i][j]))

    def ancestor_matrix_to_adjacency_matrix(ancestors: List[List[bool]]):
        size = len(ancestors)
        adjancency: List[List[bool]] =  [[False for i in range(size)] for j in range(size)]

        for i in range(size):
            for j in range(size):
                adjancency[i][j] = ancestors[i][j]

        for k in range(size):
            for l in range(size):
                for m in range(size):
                    if ancestors[k][l] and ancestors[l][m] and ancestors[k][m]:
                        adjancency[k][m] = False

        return adjancency

    def to_json_str(self):
        size = len(self.git_nodes)
        nodes = []
        links = []
        for i in range(size):
            ndc = self.git_nodes[i]
            # print("ndc.id:"+ndc.id)
            nn = self.id_to_branch.get(ndc.id)
            if nn==None:
                nn = []

            nodes.append({
                "id": i,
                "date": ndc.date,
                "inner": ndc.inner_node,
                "names": nn,
                "name": ndc.id[0:10]
            })

        for i in range(size):
            for j in range(size):
                # print("C:"+str(i)+","+str(j)+","+str(self.commit_count[i][j]))
                if self.commit_count[i][j] == 0:
                    continue
                links.append({
                    "source": i,
                    "target": j,
                    "commit_count": self.commit_count[i][j]
                })

        return json.dumps({'nodes': nodes, 'links': links}, indent=4)

    def build(self):
        uniq_branches = self.find_ids(self.branches)
        # for s in uniq_branches:
        #      print("x="+s)
        self.add_common_ancestors(uniq_branches)
        self.fill_graph()


# Initialize parser
parser = argparse.ArgumentParser()

# Adding optional argument
parser.add_argument("REPO_PATH", help="The repo path", nargs=1)
parser.add_argument("FILE", help="The branch files", nargs=1)


if __name__ == '__main__':
    args = parser.parse_args()

    fin = args.FILE[0]
    dir = args.REPO_PATH[0].strip()
    branches = []
    with open(fin) as f:
        for l in f.read().splitlines():
            l = l.strip()
            if len(l) > 0:
                branches.append(l)

    gt = GitTree()
    gt.init(dir, branches)
    gt.build()
    print(gt.to_json_str())

